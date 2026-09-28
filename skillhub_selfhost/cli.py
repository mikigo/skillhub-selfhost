import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def admin_init():
    """交互式创建管理员用户"""
    from skillhub_selfhost.config import Config
    from skillhub_selfhost.db import init_db, close_db
    from skillhub_selfhost.auth.service import register_user
    import asyncio

    config = Config()
    asyncio.run(init_db(config.db_url))

    username = typer.prompt("管理员用户名")
    password = typer.prompt("管理员密码", hide_input=True)

    asyncio.run(register_user(username, password, is_admin=True, status="active"))
    asyncio.run(close_db())
    typer.echo(f"管理员 {username} 创建成功")

@app.command()
def server_start(
    host: str = typer.Option("0.0.0.0", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
):
    """启动 skillhub 服务"""
    import sys
    import asyncio
    from skillhub_selfhost.config import Config
    from skillhub_selfhost.db import init_db
    from skillhub_selfhost.logging_config import setup_logging

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = Config(host=host, port=port)
    setup_logging(config.base_dir, config.log_level)
    config.skills_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db(config.db_url))
    loop.close()

    import uvicorn
    typer.echo(f"skillhub 启动: http://{host}:{port}")
    try:
        uvicorn.run(
            "skillhub_selfhost.main:create_app",
            factory=True,
            host=host,
            port=port,
            log_config=None,
        )
    except KeyboardInterrupt:
        typer.echo("服务已停止")

if __name__ == "__main__":
    app()