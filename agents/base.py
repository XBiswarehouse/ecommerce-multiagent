"""Agent基类 - 完整版"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import yaml
import logging
import hashlib
import json
import time
from pathlib import Path
import sys
from functools import lru_cache
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from config import ZHIPU_API_KEY, ZHIPU_MODEL, ENABLE_CACHE, CACHE_SIZE, LOG_LEVEL, LOG_FILE


class BaseAgent(ABC):
    """所有Agent的基类"""
    
    # 类级别缓存（共享）
    _llm_cache = {}
    _cache_hits = 0
    _cache_misses = 0
    _total_time = 0
    _call_count = 0
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.logger = self._setup_logger()
        self.prompt = self._load_prompt()
        self.llm = self._init_llm() if ZHIPU_API_KEY and ZHIPU_API_KEY != "你的智谱API Key" else None
        
        if not self.llm:
            self.logger.warning("LLM未初始化，将使用默认规则")
    
    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger(f"agent.{self.name}")
        logger.setLevel(getattr(logging, LOG_LEVEL))
        
        if not logger.handlers:
            # 控制台输出
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件输出
            file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
            file_formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _load_prompt(self) -> str:
        """加载提示词"""
        prompt_path = Path(__file__).parent.parent / f"prompts/{self.name}.yaml"
        if prompt_path.exists():
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('system_prompt', f"你是{self.role}")
            except Exception as e:
                self.logger.warning(f"加载提示词失败: {e}")
        return f"你是{self.role}"
    
    def _init_llm(self):
        """初始化智谱LLM"""
        try:
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=ZHIPU_API_KEY)
            self.logger.info(f"LLM初始化成功: {ZHIPU_MODEL}")
            return client
        except Exception as e:
            self.logger.warning(f"智谱LLM初始化失败: {e}")
            return None
    
    def _get_cache_key(self, prompt: str) -> str:
        """生成缓存key"""
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()
    
    def _call_llm(self, user_message: str, temperature: float = 0.7, use_cache: bool = True, max_retries: int = 3) -> str:
        """调用智谱LLM（带缓存、重试）"""
        if not self.llm:
            self.logger.warning("LLM未初始化，返回Mock响应")
            return f"[Mock] {self.role} 分析完成"
        
        # 构建完整prompt
        full_prompt = f"{self.prompt}\n\n{user_message}"
        
        # 检查缓存
        if use_cache and ENABLE_CACHE:
            cache_key = self._get_cache_key(full_prompt)
            if cache_key in self._llm_cache:
                self._cache_hits += 1
                hit_rate = self._cache_hits / (self._cache_hits + self._cache_misses) * 100 if (self._cache_hits + self._cache_misses) > 0 else 0
                self.logger.debug(f"缓存命中 (命中率: {hit_rate:.1f}%)")
                return self._llm_cache[cache_key]
            self._cache_misses += 1
        
        # 调用LLM（带重试）
        start_time = time.time()
        for attempt in range(max_retries):
            try:
                response = self.llm.chat.completions.create(
                    model=ZHIPU_MODEL,
                    messages=[
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=temperature,
                    timeout=30
                )
                result = response.choices[0].message.content
                
                # 记录耗时
                elapsed = time.time() - start_time
                self._total_time += elapsed
                self._call_count += 1
                self.logger.debug(f"LLM调用成功，耗时: {elapsed:.2f}s")
                
                # 存入缓存
                if use_cache and ENABLE_CACHE:
                    cache_key = self._get_cache_key(full_prompt)
                    if len(self._llm_cache) > CACHE_SIZE:
                        first_key = next(iter(self._llm_cache))
                        del self._llm_cache[first_key]
                    self._llm_cache[cache_key] = result
                
                return result
                
            except Exception as e:
                self.logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    self.logger.error(f"LLM调用最终失败: {e}")
                    return f"[错误] {self.role} 分析失败: {str(e)}"
        
        return f"[错误] {self.role} 分析失败"
    
    def clear_cache(self):
        """清空缓存"""
        self._llm_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.info("缓存已清空")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._cache_hits + self._cache_misses
        return {
            "size": len(self._llm_cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._cache_hits / total * 100 if total > 0 else 0,
            "avg_time": self._total_time / self._call_count if self._call_count > 0 else 0,
            "total_calls": self._call_count
        }
    
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务 - 子类必须实现"""
        pass