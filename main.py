import subprocess
import sys
import os
import signal
import time
import socket
from pathlib import Path

project_root = Path(__file__).parent
backend_dir = project_root / "backend"
frontend_dir = project_root / "frontend"

processes = []
BACKEND_PORT = 8001
FRONTEND_PORT = 3000


def signal_handler(signum, frame):
    print("\n正在停止所有服务...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("所有服务已停止")
    sys.exit(0)


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_port_process(port):
    if not is_port_in_use(port):
        return True
    
    print(f"端口 {port} 已被占用，正在尝试释放...")
    
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        except Exception:
            pass
    else:
        try:
            subprocess.run(
                f'lsof -ti:{port} | xargs kill -9 2>/dev/null || true',
                shell=True,
                capture_output=True
            )
        except Exception:
            pass
    
    time.sleep(1)
    
    if is_port_in_use(port):
        print(f"警告: 无法释放端口 {port}，请手动关闭占用该端口的进程")
        return False
    
    print(f"端口 {port} 已释放")
    return True


def check_dependencies():
    if not (backend_dir / "requirements.txt").exists():
        print("错误: 找不到后端目录")
        sys.exit(1)

    if not (frontend_dir / "package.json").exists():
        print("错误: 找不到前端目录")
        sys.exit(1)

    venv_path = backend_dir / ".venv"
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"

    need_install = False
    if not venv_path.exists():
        print("正在创建后端虚拟环境...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        need_install = True
    else:
        try:
            result = subprocess.run(
                [str(python_path), "-c", "import uvicorn"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("检测到缺少依赖，重新安装...")
                need_install = True
            else:
                print("虚拟环境已存在，跳过创建")
        except Exception as e:
            print(f"检查依赖时出错: {e}")
            need_install = True

    if need_install:
        print("正在安装后端依赖...")
        subprocess.run([str(pip_path), "install", "-r", str(backend_dir / "requirements.txt")], check=True)

    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("正在安装前端依赖...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), shell=True, check=True)
    else:
        print("前端依赖已安装，跳过安装")

    return python_path


def start_backend(python_path):
    print(f"正在启动后端服务 (端口 {BACKEND_PORT})...")
    
    proc = subprocess.Popen(
        [str(python_path), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--reload"],
        cwd=str(backend_dir),
    )
    processes.append(proc)
    return proc


def start_frontend():
    print(f"正在启动前端服务 (端口 {FRONTEND_PORT})...")
    
    if sys.platform == "win32":
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            shell=True,
        )
    else:
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
        )
    processes.append(proc)
    return proc


def main():
    print("=" * 50)
    print("DataDrivenTrader 一键启动")
    print("=" * 50)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    kill_port_process(BACKEND_PORT)
    kill_port_process(FRONTEND_PORT)
    
    python_path = check_dependencies()
    
    backend_proc = start_backend(python_path)
    time.sleep(2)
    
    frontend_proc = start_frontend()
    
    print("\n" + "=" * 50)
    print("服务启动成功!")
    print(f"后端地址: http://localhost:{BACKEND_PORT}")
    print(f"前端地址: http://localhost:{FRONTEND_PORT}")
    print(f"API文档:  http://localhost:{BACKEND_PORT}/docs")
    print("按 Ctrl+C 停止所有服务")
    print("=" * 50 + "\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
