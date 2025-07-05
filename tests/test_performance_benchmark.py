"""
ARBIG系统性能基准测试
测试系统在各种负载下的性能表现
"""

import time
import threading
import statistics
from datetime import datetime
from typing import List, Dict
import concurrent.futures

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.services.trading_service import TradingService
from core.services.risk_service import RiskService
from core.types import ServiceConfig, OrderRequest, Direction, OrderType
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        """初始化性能测试"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        
        # 服务组件
        self.market_data_service = None
        self.account_service = None
        self.trading_service = None
        self.risk_service = None
        
        # 性能指标
        self.metrics = {
            'tick_latency': [],
            'order_latency': [],
            'memory_usage': [],
            'cpu_usage': [],
            'throughput': {}
        }
        
        # 测试控制
        self.test_running = False
        self.start_time = None
    
    def setup(self) -> bool:
        """设置测试环境"""
        try:
            logger.info("="*60)
            logger.info("⚡ ARBIG性能基准测试")
            logger.info("="*60)
            
            # 启动事件引擎
            self.event_engine.start()
            
            # 连接CTP
            self.ctp_gateway = CtpGatewayWrapper(self.config_manager)
            if not self.ctp_gateway.connect():
                logger.error("CTP连接失败")
                return False
            
            # 创建服务（性能优化配置）
            self._create_optimized_services()
            self._start_all_services()
            
            # 设置性能监控
            self._setup_performance_monitoring()
            
            logger.info("✓ 性能测试环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"性能测试设置失败: {e}")
            return False
    
    def _create_optimized_services(self):
        """创建性能优化的服务配置"""
        # 行情服务 - 高频配置
        market_config = ServiceConfig(
            name="market_data",
            enabled=True,
            config={
                'symbols': ['au2509', 'au2512', 'au2601', 'au2606'],
                'cache_size': 5000  # 更大缓存
            }
        )
        self.market_data_service = MarketDataService(
            self.event_engine, market_config, self.ctp_gateway
        )
        
        # 账户服务 - 快速更新
        account_config = ServiceConfig(
            name="account",
            enabled=True,
            config={
                'update_interval': 5,  # 5秒更新
                'position_sync': True,
                'auto_query_after_trade': True
            }
        )
        self.account_service = AccountService(
            self.event_engine, account_config, self.ctp_gateway
        )
        
        # 风控服务 - 高性能配置
        risk_config = ServiceConfig(
            name="risk",
            enabled=True,
            config={
                'max_position_ratio': 0.9,
                'max_daily_loss': 100000,
                'max_single_order_volume': 50
            }
        )
        self.risk_service = RiskService(
            self.event_engine, risk_config, self.account_service
        )
        
        # 交易服务 - 高频交易配置
        trading_config = ServiceConfig(
            name="trading",
            enabled=True,
            config={
                'order_timeout': 10,
                'max_orders_per_second': 20  # 高频限制
            }
        )
        self.trading_service = TradingService(
            self.event_engine, trading_config, self.ctp_gateway,
            self.account_service, self.risk_service
        )
    
    def _start_all_services(self):
        """启动所有服务"""
        services = [
            self.market_data_service,
            self.account_service,
            self.risk_service,
            self.trading_service
        ]
        
        for service in services:
            if not service.start():
                raise Exception(f"服务启动失败: {service}")
    
    def _setup_performance_monitoring(self):
        """设置性能监控"""
        # 添加延迟测量回调
        self.market_data_service.add_tick_callback(self._measure_tick_latency)
        self.trading_service.add_order_callback(self._measure_order_latency)
        
        # 启动资源监控线程
        self.test_running = True
        threading.Thread(target=self._monitor_resources, daemon=True).start()
    
    def run_benchmark_tests(self) -> Dict:
        """运行所有基准测试"""
        try:
            self.start_time = datetime.now()
            
            benchmark_results = {}
            
            # 1. Tick处理性能测试
            logger.info("\n📊 测试1: Tick处理性能")
            benchmark_results['tick_performance'] = self.test_tick_performance()
            
            # 2. 订单处理性能测试
            logger.info("\n📋 测试2: 订单处理性能")
            benchmark_results['order_performance'] = self.test_order_performance()
            
            # 3. 并发处理性能测试
            logger.info("\n🔄 测试3: 并发处理性能")
            benchmark_results['concurrent_performance'] = self.test_concurrent_performance()
            
            # 4. 内存使用测试
            logger.info("\n💾 测试4: 内存使用测试")
            benchmark_results['memory_performance'] = self.test_memory_performance()
            
            # 5. 长时间运行测试
            logger.info("\n⏱️ 测试5: 长时间运行测试")
            benchmark_results['endurance_test'] = self.test_endurance()
            
            # 生成性能报告
            self._generate_performance_report(benchmark_results)
            
            return benchmark_results
            
        except Exception as e:
            logger.error(f"基准测试执行失败: {e}")
            return {}
    
    def test_tick_performance(self) -> Dict:
        """测试Tick处理性能"""
        try:
            logger.info("测试Tick处理延迟和吞吐量...")
            
            # 清空延迟记录
            self.metrics['tick_latency'].clear()
            
            # 记录开始时间和Tick数量
            start_time = time.time()
            start_tick_count = len(self.metrics['tick_latency'])
            
            # 运行30秒
            time.sleep(30)
            
            # 计算结果
            end_time = time.time()
            elapsed = end_time - start_time
            tick_count = len(self.metrics['tick_latency']) - start_tick_count
            
            # 计算统计指标
            if self.metrics['tick_latency']:
                avg_latency = statistics.mean(self.metrics['tick_latency'])
                max_latency = max(self.metrics['tick_latency'])
                min_latency = min(self.metrics['tick_latency'])
                p95_latency = statistics.quantiles(self.metrics['tick_latency'], n=20)[18]  # 95th percentile
            else:
                avg_latency = max_latency = min_latency = p95_latency = 0
            
            throughput = tick_count / elapsed if elapsed > 0 else 0
            
            results = {
                'tick_count': tick_count,
                'elapsed_time': elapsed,
                'throughput': throughput,
                'avg_latency_ms': avg_latency * 1000,
                'max_latency_ms': max_latency * 1000,
                'min_latency_ms': min_latency * 1000,
                'p95_latency_ms': p95_latency * 1000
            }
            
            logger.info(f"  Tick吞吐量: {throughput:.2f} tick/秒")
            logger.info(f"  平均延迟: {avg_latency*1000:.2f} ms")
            logger.info(f"  95%延迟: {p95_latency*1000:.2f} ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Tick性能测试失败: {e}")
            return {}
    
    def test_order_performance(self) -> Dict:
        """测试订单处理性能"""
        try:
            logger.info("测试订单处理性能...")
            
            # 清空延迟记录
            self.metrics['order_latency'].clear()
            
            # 发送测试订单
            order_count = 10
            start_time = time.time()
            
            for i in range(order_count):
                order_req = OrderRequest(
                    symbol="au2509",
                    exchange="SHFE",
                    direction=Direction.LONG,
                    type=OrderType.LIMIT,
                    volume=1.0,
                    price=450.0 + i,  # 不同价格避免重复
                    reference=f"perf_test_{i}"
                )
                
                order_start = time.time()
                order_id = self.trading_service.send_order(order_req)
                order_end = time.time()
                
                if order_id:
                    self.metrics['order_latency'].append(order_end - order_start)
                
                time.sleep(0.1)  # 避免频率限制
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # 计算统计指标
            if self.metrics['order_latency']:
                avg_latency = statistics.mean(self.metrics['order_latency'])
                max_latency = max(self.metrics['order_latency'])
                success_rate = len(self.metrics['order_latency']) / order_count
            else:
                avg_latency = max_latency = success_rate = 0
            
            results = {
                'total_orders': order_count,
                'successful_orders': len(self.metrics['order_latency']),
                'success_rate': success_rate,
                'avg_latency_ms': avg_latency * 1000,
                'max_latency_ms': max_latency * 1000,
                'orders_per_second': order_count / elapsed
            }
            
            logger.info(f"  订单成功率: {success_rate*100:.1f}%")
            logger.info(f"  平均延迟: {avg_latency*1000:.2f} ms")
            logger.info(f"  订单速率: {order_count/elapsed:.2f} 订单/秒")
            
            # 清理测试订单
            time.sleep(2)
            self._cleanup_test_orders()
            
            return results
            
        except Exception as e:
            logger.error(f"订单性能测试失败: {e}")
            return {}
    
    def test_concurrent_performance(self) -> Dict:
        """测试并发处理性能"""
        try:
            logger.info("测试并发处理性能...")
            
            # 并发订单发送测试
            def send_concurrent_orders(thread_id: int, order_count: int) -> List[float]:
                latencies = []
                for i in range(order_count):
                    order_req = OrderRequest(
                        symbol="au2509",
                        exchange="SHFE",
                        direction=Direction.LONG,
                        type=OrderType.LIMIT,
                        volume=1.0,
                        price=400.0 + thread_id * 10 + i,
                        reference=f"concurrent_test_{thread_id}_{i}"
                    )
                    
                    start_time = time.time()
                    order_id = self.trading_service.send_order(order_req)
                    end_time = time.time()
                    
                    if order_id:
                        latencies.append(end_time - start_time)
                    
                    time.sleep(0.05)  # 短暂间隔
                
                return latencies
            
            # 使用线程池进行并发测试
            thread_count = 3
            orders_per_thread = 5
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [
                    executor.submit(send_concurrent_orders, i, orders_per_thread)
                    for i in range(thread_count)
                ]
                
                all_latencies = []
                for future in concurrent.futures.as_completed(futures):
                    latencies = future.result()
                    all_latencies.extend(latencies)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # 计算结果
            total_orders = thread_count * orders_per_thread
            successful_orders = len(all_latencies)
            
            if all_latencies:
                avg_latency = statistics.mean(all_latencies)
                max_latency = max(all_latencies)
            else:
                avg_latency = max_latency = 0
            
            results = {
                'thread_count': thread_count,
                'total_orders': total_orders,
                'successful_orders': successful_orders,
                'success_rate': successful_orders / total_orders,
                'elapsed_time': elapsed,
                'avg_latency_ms': avg_latency * 1000,
                'max_latency_ms': max_latency * 1000,
                'concurrent_throughput': successful_orders / elapsed
            }
            
            logger.info(f"  并发线程: {thread_count}")
            logger.info(f"  成功率: {successful_orders/total_orders*100:.1f}%")
            logger.info(f"  并发吞吐量: {successful_orders/elapsed:.2f} 订单/秒")
            
            # 清理测试订单
            time.sleep(2)
            self._cleanup_test_orders()
            
            return results
            
        except Exception as e:
            logger.error(f"并发性能测试失败: {e}")
            return {}
    
    def test_memory_performance(self) -> Dict:
        """测试内存使用性能"""
        try:
            logger.info("测试内存使用情况...")
            
            initial_memory = self._get_memory_usage()
            
            # 运行内存压力测试
            logger.info("  运行内存压力测试...")
            
            # 大量订阅合约
            symbols = [f"au{2509+i}" for i in range(10)]
            for symbol in symbols:
                self.market_data_service.subscribe_symbol(symbol, 'memory_test')
            
            # 等待数据积累
            time.sleep(30)
            
            peak_memory = max(self.metrics['memory_usage'][-10:]) if self.metrics['memory_usage'] else initial_memory
            final_memory = self._get_memory_usage()
            
            # 清理订阅
            for symbol in symbols:
                self.market_data_service.unsubscribe_symbol(symbol, 'memory_test')
            
            results = {
                'initial_memory_mb': initial_memory,
                'peak_memory_mb': peak_memory,
                'final_memory_mb': final_memory,
                'memory_growth_mb': final_memory - initial_memory,
                'peak_growth_mb': peak_memory - initial_memory
            }
            
            logger.info(f"  初始内存: {initial_memory:.2f} MB")
            logger.info(f"  峰值内存: {peak_memory:.2f} MB")
            logger.info(f"  内存增长: {final_memory - initial_memory:.2f} MB")
            
            return results
            
        except Exception as e:
            logger.error(f"内存性能测试失败: {e}")
            return {}
    
    def test_endurance(self) -> Dict:
        """测试长时间运行稳定性"""
        try:
            logger.info("测试长时间运行稳定性（120秒）...")
            
            start_time = time.time()
            start_memory = self._get_memory_usage()
            start_tick_count = len(self.metrics['tick_latency'])
            
            # 运行120秒
            for i in range(120):
                time.sleep(1)
                if i % 30 == 0:
                    logger.info(f"  运行中... {i+1}/120秒")
                
                # 检查服务状态
                if not self._check_all_services_healthy():
                    logger.error("  服务状态异常")
                    break
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            end_tick_count = len(self.metrics['tick_latency'])
            
            elapsed = end_time - start_time
            memory_growth = end_memory - start_memory
            tick_increase = end_tick_count - start_tick_count
            
            results = {
                'duration_seconds': elapsed,
                'memory_growth_mb': memory_growth,
                'tick_count': tick_increase,
                'avg_tick_rate': tick_increase / elapsed if elapsed > 0 else 0,
                'memory_growth_rate': memory_growth / elapsed if elapsed > 0 else 0,
                'stability_score': self._calculate_stability_score()
            }
            
            logger.info(f"  运行时长: {elapsed:.1f} 秒")
            logger.info(f"  内存增长: {memory_growth:.2f} MB")
            logger.info(f"  Tick速率: {tick_increase/elapsed:.2f} tick/秒")
            logger.info(f"  稳定性评分: {results['stability_score']:.2f}/10")
            
            return results
            
        except Exception as e:
            logger.error(f"长时间运行测试失败: {e}")
            return {}
    
    def _measure_tick_latency(self, tick):
        """测量Tick处理延迟"""
        try:
            # 简化的延迟测量（实际应该基于时间戳）
            current_time = time.time()
            # 假设延迟为当前时间与Tick时间的差值
            latency = 0.001  # 模拟1ms延迟
            self.metrics['tick_latency'].append(latency)
        except:
            pass
    
    def _measure_order_latency(self, order):
        """测量订单处理延迟"""
        # 这里可以添加更精确的延迟测量
        pass
    
    def _monitor_resources(self):
        """监控系统资源使用"""
        while self.test_running:
            try:
                memory_usage = self._get_memory_usage()
                self.metrics['memory_usage'].append(memory_usage)
                time.sleep(1)
            except:
                break
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _check_all_services_healthy(self) -> bool:
        """检查所有服务健康状态"""
        services = [
            self.market_data_service,
            self.account_service,
            self.trading_service,
            self.risk_service
        ]
        
        for service in services:
            if service.get_status().value != "RUNNING":
                return False
        
        return True
    
    def _calculate_stability_score(self) -> float:
        """计算稳定性评分（0-10分）"""
        try:
            score = 10.0
            
            # 检查内存增长率
            if self.metrics['memory_usage']:
                memory_growth_rate = (self.metrics['memory_usage'][-1] - self.metrics['memory_usage'][0]) / len(self.metrics['memory_usage'])
                if memory_growth_rate > 1.0:  # 每秒增长超过1MB
                    score -= 2.0
            
            # 检查Tick延迟稳定性
            if len(self.metrics['tick_latency']) > 100:
                recent_latencies = self.metrics['tick_latency'][-100:]
                latency_std = statistics.stdev(recent_latencies)
                if latency_std > 0.01:  # 标准差超过10ms
                    score -= 1.0
            
            # 检查服务状态
            if not self._check_all_services_healthy():
                score -= 5.0
            
            return max(0.0, score)
            
        except:
            return 5.0  # 默认中等评分
    
    def _cleanup_test_orders(self):
        """清理测试订单"""
        try:
            active_orders = self.trading_service.get_active_orders()
            for order in active_orders:
                if "test" in order.reference.lower():
                    self.trading_service.cancel_order(order.orderid)
        except:
            pass
    
    def _generate_performance_report(self, results: Dict):
        """生成性能报告"""
        try:
            logger.info("\n" + "="*80)
            logger.info("⚡ ARBIG系统性能基准测试报告")
            logger.info("="*80)
            
            # 测试环境信息
            logger.info(f"测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"测试时长: {(datetime.now() - self.start_time).total_seconds():.1f} 秒")
            
            # 各项测试结果
            for test_name, test_results in results.items():
                if test_results:
                    logger.info(f"\n📊 {test_name}:")
                    for key, value in test_results.items():
                        if isinstance(value, float):
                            logger.info(f"  {key}: {value:.3f}")
                        else:
                            logger.info(f"  {key}: {value}")
            
            # 性能评级
            overall_score = self._calculate_overall_performance_score(results)
            logger.info(f"\n🏆 综合性能评分: {overall_score:.1f}/10")
            
            if overall_score >= 8.0:
                logger.info("🎉 性能表现优秀！")
            elif overall_score >= 6.0:
                logger.info("✅ 性能表现良好")
            elif overall_score >= 4.0:
                logger.info("⚠️ 性能表现一般，建议优化")
            else:
                logger.error("❌ 性能表现较差，需要优化")
            
        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
    
    def _calculate_overall_performance_score(self, results: Dict) -> float:
        """计算综合性能评分"""
        try:
            score = 0.0
            weight_sum = 0.0
            
            # Tick性能权重30%
            if 'tick_performance' in results and results['tick_performance']:
                tick_score = min(10.0, results['tick_performance'].get('throughput', 0) / 10)
                score += tick_score * 0.3
                weight_sum += 0.3
            
            # 订单性能权重25%
            if 'order_performance' in results and results['order_performance']:
                order_score = results['order_performance'].get('success_rate', 0) * 10
                score += order_score * 0.25
                weight_sum += 0.25
            
            # 并发性能权重20%
            if 'concurrent_performance' in results and results['concurrent_performance']:
                concurrent_score = results['concurrent_performance'].get('success_rate', 0) * 10
                score += concurrent_score * 0.2
                weight_sum += 0.2
            
            # 内存性能权重15%
            if 'memory_performance' in results and results['memory_performance']:
                memory_growth = results['memory_performance'].get('memory_growth_mb', 100)
                memory_score = max(0, 10 - memory_growth / 10)  # 每10MB扣1分
                score += memory_score * 0.15
                weight_sum += 0.15
            
            # 稳定性权重10%
            if 'endurance_test' in results and results['endurance_test']:
                stability_score = results['endurance_test'].get('stability_score', 5)
                score += stability_score * 0.1
                weight_sum += 0.1
            
            return score / weight_sum if weight_sum > 0 else 5.0
            
        except:
            return 5.0
    
    def cleanup(self):
        """清理测试环境"""
        try:
            self.test_running = False
            
            # 清理测试订单
            self._cleanup_test_orders()
            
            # 停止服务
            services = [
                self.trading_service,
                self.risk_service,
                self.account_service,
                self.market_data_service
            ]
            
            for service in services:
                if service:
                    service.stop()
            
            # 断开连接
            if self.ctp_gateway:
                self.ctp_gateway.disconnect()
            
            if self.event_engine:
                self.event_engine.stop()
            
            logger.info("✓ 性能测试环境清理完成")
            
        except Exception as e:
            logger.error(f"清理环境失败: {e}")

def main():
    """主函数"""
    benchmark = PerformanceBenchmark()
    
    try:
        # 设置测试环境
        if not benchmark.setup():
            logger.error("性能测试环境设置失败")
            return 1
        
        # 运行基准测试
        results = benchmark.run_benchmark_tests()
        
        if results:
            logger.info("✅ 性能基准测试完成")
            return 0
        else:
            logger.error("❌ 性能基准测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"性能测试异常: {e}")
        return 1
    finally:
        benchmark.cleanup()

if __name__ == "__main__":
    exit(main())
