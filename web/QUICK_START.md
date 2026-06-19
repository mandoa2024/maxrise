# Mini-Drop 前端快速启动

## 🚀 快速启动

### 1. 安装依赖

```bash
cd web
npm install
```

### 2. 开发模式

```bash
npm run dev
```

浏览器访问: `http://localhost:3000`

### 3. 生产构建

```bash
npm run build
```

构建输出在 `dist/` 目录

### 4. 预览生产版本

```bash
npm run preview
```

## 🎨 新 UI 特性

### 深色专业主题
- 深色渐变背景
- 高对比度文本
- 玻璃态效果

### 现代化组件
- SVG 图标 (Heroicons)
- 响应式网格布局
- 平滑动画过渡

### 彩色状态编码
- 🟢 绿色: ONLINE, DONE
- 🔴 红色: OFFLINE, FAILED  
- 🔵 蓝色: RUNNING, UPLOADING
- 🟡 琥珀: PENDING, RECOVERED

## 🛠️ 技术栈

- **React 19** - UI 框架
- **Vite 7** - 构建工具
- **Tailwind CSS v4** - 样式框架
- **Fira Sans/Code** - 字体系统

## 📱 响应式支持

- 📱 Mobile: 375px+
- 📱 Tablet: 768px+
- 💻 Desktop: 1024px+
- 🖥️ Large Desktop: 1440px+

## ♿ 可访问性

- ✅ WCAG AA 标准 (对比度 4.5:1+)
- ✅ Keyboard 导航完全支持
- ✅ Screen Reader 友好
- ✅ 减少动画选项 (prefers-reduced-motion)

## 🐛 故障排查

### 端口被占用

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# 或使用其他端口
npm run dev -- --port 3001
```

### 依赖安装失败

```bash
# 清除缓存
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 构建失败

确保 Node.js 版本 >= 18:

```bash
node --version
```

## 📚 更多文档

- [UI_UPGRADE.md](./UI_UPGRADE.md) - 详细的 UI 优化说明
- [DESIGN_COMPARISON.md](./DESIGN_COMPARISON.md) - 设计对比

---

**优化基于**: [UI/UX Pro Max Skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
