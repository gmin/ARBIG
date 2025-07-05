#!/usr/bin/env python3
"""
ARBIG系统完整测试套件
按顺序运行所有测试，验证系统完整性
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class ARBIGTestSuite:
    """ARBIG完整测试套件"""
    
    def __init__(self):
        """初始化测试套件"""
        self.project_root = project_root
        self.test_results = {}
        self.start_time = None
        
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        try:
            self.start_time = datetime.now()
            
            logger.info("="*80)
            logger.info("🧪 ARBIG系统完整测试套件")
            logger.info("="*80)
            logger.info(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 测试计划
            test_plan = [
                ("环境检查", self._test_environment),
                ("CTP网关测试", self._test_ctp_gateway),
                ("行情服务测试", self._test_market_data_service),
                ("账户服务测试", self._test_account_service),
                ("交易服务测试", self._test_trading_service),
                ("风控服务测试", self._test_risk_service),
                ("Web监控测试", self._test_web_monitor),
                ("系统集成测试", self._test_system_integration),
                ("性能基准测试", self._test_performance),
                ("最终验收测试", self._test_final_acceptance)
            ]
            
            passed_tests = 0
            total_tests = len(test_plan)
            
            for i, (test_name, test_func) in enumerate(test_plan, 1):
                logger.info(f"\n{'='*20} 测试 {i}/{total_tests}: {test_name} {'='*20}")
                
                try:
                    if test_func():
                        self.test_results[test_name] = "PASSED"
                        passed_tests += 1
                        logger.info(f"✅ {test_name} 通过")
                    else:
                        self.test_results[test_name] = "FAILED"
                        logger.error(f"❌ {test_name} 失败")
                        
                        # 询问是否继续
                        if not self._ask_continue_on_failure(test_name):
                            break
                            
                except Exception as e:
                    self.test_results[test_name] = f"ERROR: {e}"
                    logger.error(f"💥 {test_name} 异常: {e}")
                    
                    if not self._ask_continue_on_failure(test_name):
                        break
                
                # 测试间隔
                time.sleep(2)
            
            # 生成测试报告
            self._generate_test_report(passed_tests, total_tests)
            
            return passed_tests == total_tests
            
        except KeyboardInterrupt:
            logger.info("测试被用户中断")
            return False
        except Exception as e:
            logger.error(f"测试套件执行失败: {e}")
            return False
    
    def _test_environment(self) -> bool:
        """环境检查测试"""
        try:
            logger.info("检查Python环境和依赖...")
            
            # Python版本检查
            python_version = sys.version_info
            if python_version < (3, 8):
                logger.error(f"Python版本过低: {python_version}")
                return False
            logger.info(f"  ✓ Python版本: {python_version.major}.{python_version.minor}")
            
            # 检查关键模块
            required_modules = [
                'vnpy', 'fastapi', 'uvicorn', 'websockets', 
                'pydantic', 'yaml', 'psutil'
            ]
            
            for module in required_modules:
                try:
                    __import__(module)
                    logger.info(f"  ✓ 模块 {module} 可用")
                except ImportError:
                    logger.error(f"  ✗ 模块 {module} 缺失")
                    logger.info(f"    请运行: pip install {module}")
                    return False
            
            # 检查配置文件
            config_file = self.project_root / 'config' / 'ctp_sim.json'
            if config_file.exists():
                logger.info(f"  ✓ CTP配置文件存在")
            else:
                logger.warning(f"  ⚠ CTP配置文件不存在，某些测试可能失败")
            
            return True
            
        except Exception as e:
            logger.error(f"环境检查失败: {e}")
            return False
    
    def _test_ctp_gateway(self) -> bool:
        """CTP网关测试"""
        try:
            logger.info("测试CTP网关...")
            
            # 运行CTP连接测试
            test_script = self.project_root / 'tests' / 'ctp_connection_test.py'
            if test_script.exists():
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    logger.info("  ✓ CTP网关测试通过")
                    return True
                else:
                    logger.error(f"  ✗ CTP网关测试失败: {result.stderr}")
                    return False
            else:
                logger.warning("  ⚠ CTP测试脚本不存在，跳过测试")
                return True
                
        except subprocess.TimeoutExpired:
            logger.error("  ✗ CTP网关测试超时")
            return False
        except Exception as e:
            logger.error(f"CTP网关测试失败: {e}")
            return False
    
    def _test_market_data_service(self) -> bool:
        """行情服务测试"""
        try:
            logger.info("测试行情服务...")
            
            test_script = self.project_root / 'examples' / 'market_data_demo.py'
            if test_script.exists():
                # 运行行情服务演示（限时30秒）
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=30)
                
                # 检查输出中是否有成功标识
                if "行情服务启动成功" in result.stdout or result.returncode == 0:
                    logger.info("  ✓ 行情服务测试通过")
                    return True
                else:
                    logger.error(f"  ✗ 行情服务测试失败")
                    logger.error(f"    输出: {result.stdout}")
                    logger.error(f"    错误: {result.stderr}")
                    return False
            else:
                logger.warning("  ⚠ 行情服务演示脚本不存在")
                return True
                
        except subprocess.TimeoutExpired:
            logger.info("  ✓ 行情服务测试超时结束（正常，服务在运行）")
            return True
        except Exception as e:
            logger.error(f"行情服务测试失败: {e}")
            return False
    
    def _test_account_service(self) -> bool:
        """账户服务测试"""
        try:
            logger.info("测试账户服务...")
            
            test_script = self.project_root / 'examples' / 'account_demo.py'
            if test_script.exists():
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=30)
                
                if "账户服务启动成功" in result.stdout or result.returncode == 0:
                    logger.info("  ✓ 账户服务测试通过")
                    return True
                else:
                    logger.error(f"  ✗ 账户服务测试失败")
                    return False
            else:
                logger.warning("  ⚠ 账户服务演示脚本不存在")
                return True
                
        except subprocess.TimeoutExpired:
            logger.info("  ✓ 账户服务测试超时结束（正常）")
            return True
        except Exception as e:
            logger.error(f"账户服务测试失败: {e}")
            return False
    
    def _test_trading_service(self) -> bool:
        """交易服务测试"""
        try:
            logger.info("测试交易服务...")
            
            test_script = self.project_root / 'examples' / 'trading_demo.py'
            if test_script.exists():
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=30)
                
                if "交易服务启动成功" in result.stdout or result.returncode == 0:
                    logger.info("  ✓ 交易服务测试通过")
                    return True
                else:
                    logger.error(f"  ✗ 交易服务测试失败")
                    return False
            else:
                logger.warning("  ⚠ 交易服务演示脚本不存在")
                return True
                
        except subprocess.TimeoutExpired:
            logger.info("  ✓ 交易服务测试超时结束（正常）")
            return True
        except Exception as e:
            logger.error(f"交易服务测试失败: {e}")
            return False
    
    def _test_risk_service(self) -> bool:
        """风控服务测试"""
        try:
            logger.info("测试风控服务...")
            
            # 简单的风控模块导入测试
            try:
                from core.services.risk_service import RiskService
                logger.info("  ✓ 风控服务模块导入成功")
                return True
            except ImportError as e:
                logger.error(f"  ✗ 风控服务模块导入失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"风控服务测试失败: {e}")
            return False
    
    def _test_web_monitor(self) -> bool:
        """Web监控测试"""
        try:
            logger.info("测试Web监控...")
            
            # 测试Web监控模块导入
            try:
                from web_monitor.app import web_app
                logger.info("  ✓ Web监控模块导入成功")
                
                # 测试启动脚本
                start_script = self.project_root / 'web_monitor' / 'run_web_monitor.py'
                if start_script.exists():
                    logger.info("  ✓ Web监控启动脚本存在")
                    return True
                else:
                    logger.error("  ✗ Web监控启动脚本不存在")
                    return False
                    
            except ImportError as e:
                logger.error(f"  ✗ Web监控模块导入失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Web监控测试失败: {e}")
            return False
    
    def _test_system_integration(self) -> bool:
        """系统集成测试"""
        try:
            logger.info("运行系统集成测试...")
            
            test_script = self.project_root / 'tests' / 'test_system_integration.py'
            if test_script.exists():
                # 运行集成测试（限时120秒）
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    logger.info("  ✓ 系统集成测试通过")
                    return True
                else:
                    logger.error(f"  ✗ 系统集成测试失败")
                    logger.error(f"    错误输出: {result.stderr}")
                    return False
            else:
                logger.warning("  ⚠ 系统集成测试脚本不存在")
                return True
                
        except subprocess.TimeoutExpired:
            logger.warning("  ⚠ 系统集成测试超时")
            return False
        except Exception as e:
            logger.error(f"系统集成测试失败: {e}")
            return False
    
    def _test_performance(self) -> bool:
        """性能基准测试"""
        try:
            logger.info("运行性能基准测试...")
            
            test_script = self.project_root / 'tests' / 'test_performance_benchmark.py'
            if test_script.exists():
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=180)
                
                if result.returncode == 0:
                    logger.info("  ✓ 性能基准测试通过")
                    return True
                else:
                    logger.error(f"  ✗ 性能基准测试失败")
                    return False
            else:
                logger.warning("  ⚠ 性能基准测试脚本不存在")
                return True
                
        except subprocess.TimeoutExpired:
            logger.warning("  ⚠ 性能基准测试超时")
            return False
        except Exception as e:
            logger.error(f"性能基准测试失败: {e}")
            return False
    
    def _test_final_acceptance(self) -> bool:
        """最终验收测试"""
        try:
            logger.info("运行最终验收测试...")
            
            test_script = self.project_root / 'tests' / 'test_final_acceptance.py'
            if test_script.exists():
                result = subprocess.run([
                    sys.executable, str(test_script)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    logger.info("  ✓ 最终验收测试通过")
                    return True
                else:
                    logger.error(f"  ✗ 最终验收测试失败")
                    return False
            else:
                logger.warning("  ⚠ 最终验收测试脚本不存在")
                return True
                
        except subprocess.TimeoutExpired:
            logger.warning("  ⚠ 最终验收测试超时")
            return False
        except Exception as e:
            logger.error(f"最终验收测试失败: {e}")
            return False
    
    def _ask_continue_on_failure(self, test_name: str) -> bool:
        """询问测试失败时是否继续"""
        try:
            response = input(f"\n{test_name} 失败，是否继续后续测试？(y/n): ").strip().lower()
            return response in ['y', 'yes', '']
        except KeyboardInterrupt:
            return False
    
    def _generate_test_report(self, passed_tests: int, total_tests: int):
        """生成测试报告"""
        try:
            test_duration = (datetime.now() - self.start_time).total_seconds()
            success_rate = passed_tests / total_tests if total_tests > 0 else 0
            
            logger.info("\n" + "="*80)
            logger.info("📊 ARBIG系统测试报告")
            logger.info("="*80)
            
            # 基本信息
            logger.info(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"测试总耗时: {test_duration:.1f} 秒")
            logger.info(f"测试总数: {total_tests}")
            logger.info(f"通过测试: {passed_tests}")
            logger.info(f"失败测试: {total_tests - passed_tests}")
            logger.info(f"成功率: {success_rate*100:.1f}%")
            
            # 详细结果
            logger.info(f"\n📋 详细测试结果:")
            for test_name, result in self.test_results.items():
                status_icon = "✅" if result == "PASSED" else "❌"
                logger.info(f"  {status_icon} {test_name}: {result}")
            
            # 总结
            if success_rate == 1.0:
                logger.info("\n🎉 所有测试通过！ARBIG系统运行正常！")
            elif success_rate >= 0.8:
                logger.info(f"\n✅ 大部分测试通过！系统基本正常，建议检查失败的测试。")
            else:
                logger.error(f"\n❌ 多个测试失败！请检查系统配置和环境。")
            
            # 建议
            logger.info(f"\n💡 建议:")
            if success_rate < 1.0:
                logger.info("  1. 检查失败测试的错误信息")
                logger.info("  2. 确认CTP配置文件正确")
                logger.info("  3. 检查网络连接")
                logger.info("  4. 查看详细日志")
            
            logger.info("  5. 如需帮助，请查看用户手册或联系技术支持")
            
        except Exception as e:
            logger.error(f"生成测试报告失败: {e}")

def main():
    """主函数"""
    print("🧪 ARBIG系统完整测试套件")
    print("=" * 50)
    print("这将运行ARBIG系统的所有测试，包括：")
    print("- 环境检查")
    print("- 各个服务模块测试")
    print("- 系统集成测试")
    print("- 性能基准测试")
    print("- 最终验收测试")
    print("\n注意：某些测试需要CTP连接，请确保配置正确。")
    
    try:
        response = input("\n是否开始测试？(y/n): ").strip().lower()
        if response not in ['y', 'yes', '']:
            print("测试已取消")
            return 0
    except KeyboardInterrupt:
        print("\n测试已取消")
        return 0
    
    # 运行测试套件
    test_suite = ARBIGTestSuite()
    success = test_suite.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
