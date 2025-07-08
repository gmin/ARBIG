"""
ARBIG Web API 主应用
FastAPI应用的入口点，集成所有API路由
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import uuid

from .routers import system_router, services_router, strategies_router, data_router
from .models.responses import APIResponse, ErrorResponse

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG Web指挥中轴 API",
    description="ARBIG量化交易系统的Web指挥中轴API接口",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(system_router)
app.include_router(services_router)
app.include_router(strategies_router)
app.include_router(data_router)

# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error={
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None
            },
            request_id=str(uuid.uuid4())
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error={
                "code": "INTERNAL_ERROR",
                "message": "内部服务器错误",
                "details": str(exc)
            },
            request_id=str(uuid.uuid4())
        ).dict()
    )

# 根路径
@app.get("/", response_model=APIResponse)
async def root():
    """API根路径"""
    return APIResponse(
        success=True,
        message="ARBIG Web指挥中轴 API",
        data={
            "version": "1.0.0",
            "description": "ARBIG量化交易系统的Web指挥中轴API接口",
            "docs_url": "/api/docs",
            "status": "running"
        },
        request_id=str(uuid.uuid4())
    )

# 健康检查
@app.get("/health", response_model=APIResponse)
async def health_check():
    """健康检查接口"""
    return APIResponse(
        success=True,
        message="API服务运行正常",
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        request_id=str(uuid.uuid4())
    )

# API信息
@app.get("/api/info", response_model=APIResponse)
async def api_info():
    """API信息接口"""
    return APIResponse(
        success=True,
        message="API信息获取成功",
        data={
            "title": "ARBIG Web指挥中轴 API",
            "version": "1.0.0",
            "description": "ARBIG量化交易系统的Web指挥中轴API接口",
            "endpoints": {
                "system": "/api/v1/system",
                "services": "/api/v1/services",
                "strategies": "/api/v1/strategies",
                "data": "/api/v1/data"
            },
            "documentation": {
                "swagger": "/api/docs",
                "redoc": "/api/redoc"
            }
        },
        request_id=str(uuid.uuid4())
    )

# 启动函数
def start_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """启动API服务器"""
    uvicorn.run(
        "web_admin.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    start_api_server(reload=True)
