"""Agent基类 - 增强版"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import yaml
import logging
import hashlib
import json
import time
from pathlib import Path
import sys
from collections import OrderedDict
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from config import ZHIPU_API_KEY, ZHIPU_MODEL, ENABLE_CACHE, CACHE_SIZE, LOG_LEVEL, LOG_FILE


class BaseAgent(ABC):
    """所有Agent的基类 - 增强版"""
    
    # 类级别缓存（共享，使用OrderedDict实现LRU）
    _llm_cache = OrderedDict()
    _cache_hits = 0
    _cache_misses = 0
    _total_time = 0
    _call_count = 0
    _total_tokens = 0  # 新增：总token使用量
    _cache_lock = threading.Lock()  # 新增：线程锁
    
    def __init__(self, name: str, role: str, **prompt_vars):
        self.name = name
        self.role = role
        self.prompt_vars = prompt_vars  # 新增：支持动态变量
        self.logger = self._setup_logger()
        self.prompt = self._load_prompt(**prompt_vars)
        self.llm = self._init_llm() if ZHIPU_API_KEY and ZHIPU_API_KEY != "你的智谱API Key" else None
        
        if not self.llm:
            self.logger.warning("LLM未初始化，将使用默认规则")
    
    def _setup_logger(self):
        """设置日志 - 支持轮转"""
        logger = logging.getLogger(f"agent.{self.name}")
        logger.setLevel(getattr(logging, LOG_LEVEL))
        
        if not logger.handlers:
            # 控制台输出
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件输出 - 支持轮转
            file_handler = RotatingFileHandler(
                LOG_FILE, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,           # 保留5个备份
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _load_prompt(self, **kwargs) -> str:
        """加载提示词 - 支持变量替换"""
        prompt_path = Path(__file__).parent.parent / f"prompts/{self.name}.yaml"
        if prompt_path.exists():
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    template = config.get('system_prompt', f"你是{self.role}")
                    
                    # 添加默认变量
                    default_vars = {
                        'current_date': datetime.now().strftime('%Y-%m-%d'),
                        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'role': self.role
                    }
                    default_vars.update(kwargs)
                    
                    # 变量替换
                    try:
                        return template.format(**default_vars)
                    except KeyError as e:
                        self.logger.warning(f"提示词变量替换失败: {e}，使用原模板")
                        return template
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
    
    def _get_cache_key(self, user_message: str, temperature: float) -> str:
        """生成缓存key - 更精确，包含temperature"""
        data = {
            "prompt": self.prompt,
            "user_message": user_message,
            "temperature": temperature
        }
        # 使用sort_keys确保顺序一致
        return hashlib.md5(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
        ).hexdigest()
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        error_str = str(error).lower()
        
        # 不可重试的错误类型
        non_retryable = [
            "invalid api key",
            "authentication failed",
            "unauthorized",
            "rate limit exceeded",  # 限流虽然可重试，但建议等待更久
            "invalid parameter",
            "bad request"
        ]
        
        for msg in non_retryable:
            if msg in error_str:
                return False
        return True
    
    def _call_llm(self, user_message: str, temperature: float = 0.7, use_cache: bool = True, max_retries: int = 3) -> str:
        """调用智谱LLM（带缓存、重试、线程安全）"""
        if not self.llm:
            self.logger.warning("LLM未初始化，返回Mock响应")
            return f"[Mock] {self.role} 分析完成"
        
        # 使用线程锁保护缓存操作
        with self._cache_lock:
            # 检查缓存
            if use_cache and ENABLE_CACHE:
                cache_key = self._get_cache_key(user_message, temperature)
                if cache_key in self._llm_cache:
                    self._cache_hits += 1
                    # LRU: 将命中的key移到末尾
                    self._llm_cache.move_to_end(cache_key)
                    hit_rate = self._cache_hits / (self._cache_hits + self._cache_misses) * 100 if (self._cache_hits + self._cache_misses) > 0 else 0
                    self.logger.debug(f"缓存命中 (命中率: {hit_rate:.1f}%)")
                    return self._llm_cache[cache_key]
                self._cache_misses += 1
        
        # 调用LLM（带重试）
        start_time = time.time()
        last_error = None
        
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
                
                # 记录耗时和token使用
                elapsed = time.time() - start_time
                self._total_time += elapsed
                self._call_count += 1
                
                # 记录token使用（如果API返回）
                if hasattr(response, 'usage') and response.usage:
                    tokens_used = response.usage.total_tokens
                    self._total_tokens += tokens_used
                    self.logger.debug(f"LLM调用成功，耗时: {elapsed:.2f}s, Tokens: {tokens_used}")
                else:
                    self.logger.debug(f"LLM调用成功，耗时: {elapsed:.2f}s")
                
                # 存入缓存（线程安全）
                if use_cache and ENABLE_CACHE:
                    with self._cache_lock:
                        cache_key = self._get_cache_key(user_message, temperature)
                        # LRU缓存淘汰
                        if len(self._llm_cache) >= CACHE_SIZE:
                            # 删除最旧的（第一个）
                            self._llm_cache.popitem(last=False)
                        self._llm_cache[cache_key] = result
                        # 将新添加的移到末尾
                        self._llm_cache.move_to_end(cache_key)
                
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                # 判断是否可重试
                if not self._is_retryable_error(e):
                    self.logger.error(f"遇到不可重试的错误: {e}")
                    return f"[错误] {self.role} 分析失败: {str(e)}"
                
                if attempt < max_retries - 1:
                    # 指数退避，但限流错误等待更久
                    wait_time = 2 ** attempt
                    if "rate limit" in str(e).lower():
                        wait_time = 5 * (2 ** attempt)  # 限流等待更久
                    self.logger.debug(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"LLM调用最终失败: {e}")
                    return f"[错误] {self.role} 分析失败: {str(e)}"
        
        return f"[错误] {self.role} 分析失败: {str(last_error) if last_error else '未知错误'}"
    
    def clear_cache(self):
        """清空缓存（线程安全）"""
        with self._cache_lock:
            self._llm_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self.logger.info("缓存已清空")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        with self._cache_lock:
            total = self._cache_hits + self._cache_misses
            return {
                "size": len(self._llm_cache),
                "max_size": CACHE_SIZE,
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": self._cache_hits / total * 100 if total > 0 else 0,
                "avg_time": self._total_time / self._call_count if self._call_count > 0 else 0,
                "total_calls": self._call_count,
                "total_tokens": self._total_tokens,
                "estimated_cost": self._estimate_cost(self._total_tokens)  # 新增：估算成本
            }
    
    def _estimate_cost(self, total_tokens: int) -> float:
        """估算API调用成本（根据智谱价格）"""
        # 智谱GLM-4价格参考（元/千tokens）
        # 输入: 0.1元/千tokens，输出: 0.1元/千tokens
        # 这里简化计算
        return total_tokens / 1000 * 0.1
    
    def update_prompt_vars(self, **kwargs):
        """动态更新提示词变量"""
        self.prompt_vars.update(kwargs)
        self.prompt = self._load_prompt(**self.prompt_vars)
        self.logger.info(f"提示词已更新，新变量: {kwargs}")
    
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务 - 子类必须实现"""
        pass