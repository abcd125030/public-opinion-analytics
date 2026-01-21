# 创建并激活虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 升级 pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 运行项目
python analysis_service.py
