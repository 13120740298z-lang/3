# 小U - 桌面宠物

基于 Live2D Cubism SDK 的 Windows 桌面宠物，支持 AI 对话、物理效果动画、表情变化等功能。

## 功能特点

- Live2D Cubism 模型渲染
- 头发物理摆动效果
- 自动呼吸、眨眼动画
- 表情变化系统
- AI 对话功能（需要配置 API Key）
- 好感度记忆系统

## 快速开始

### 方法一：直接运行

```bash
pip install -r requirements.txt
python main.py
```

### 方法二：使用打包好的 exe

从 [Releases](https://github.com/你的用户名/你的仓库/releases) 下载最新版本的 exe 文件。

## 项目结构

```
.
├── models/UG/          # Live2D 模型文件
├── resources/         # 资源文件
├── data/              # 数据存储
├── main.py            # 主程序
├── live2d_engine.py   # Live2D 渲染引擎
└── ...
```

## 配置

在 `config.py` 中配置：

```python
API_KEY = "your-api-key-here"  # 设置你的 API Key
```

## 开发

### 构建 exe

项目使用 GitHub Actions 自动构建。推送到 main 分支后会自动生成 Windows exe 文件。

手动构建：
```bash
pip install pyinstaller
pyinstaller --onedir --windowed main.py
```

## License

MIT License
