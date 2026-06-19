# Mini-Drop Web UI 2.0

> 基于 UI/UX Pro Max Skill 的专业性能监控平台界面

[![UI Version](https://img.shields.io/badge/UI-2.0.0-blue)](./CHANGELOG.md)
[![Design System](https://img.shields.io/badge/Design-UI%2FUX%20Pro%20Max-purple)](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
[![Tailwind](https://img.shields.io/badge/Tailwind-4.3-38bdf8)](https://tailwindcss.com/)
[![React](https://img.shields.io/badge/React-19.0-61dafb)](https://react.dev/)

## ✨ 特性

- 🎨 **现代化设计** - 深色主题 + 玻璃态效果
- ⚡ **流畅交互** - 平滑动画 (150-300ms)
- 📱 **完全响应式** - Mobile to Desktop (375px - 1440px+)
- ♿ **高可访问性** - WCAG AAA 标准 (对比度 7:1)
- 🎯 **专业配色** - 数据可视化优化配色方案
- 🔍 **SVG 图标** - Heroicons 专业图标系统

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问: http://localhost:3000

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录

## 📐 设计系统

### 配色方案

| 角色 | 颜色 | 用途 |
|------|------|------|
| Primary | `#1E40AF` | 主要交互元素 |
| Secondary | `#3B82F6` | 辅助元素 |
| Accent | `#F59E0B` | 强调和 CTA |
| Background | Gradient | Slate 900 → Blue 900 |
| Text | `#F1F5F9` | 主要文本 |

### 字体系统

- **Sans**: Fira Sans (300-700) - 界面文本
- **Mono**: Fira Code (400-700) - 代码和数据

### 状态编码

- 🟢 **成功**: ONLINE, DONE (#10B981)
- 🔴 **错误**: OFFLINE, FAILED (#EF4444)
- 🔵 **运行**: RUNNING, UPLOADING (#3B82F6)
- 🟡 **警告**: PENDING, RECOVERED (#F59E0B)

## 📚 文档

| 文档 | 说明 |
|------|------|
| [QUICK_START.md](./QUICK_START.md) | 快速启动指南 |
| [UI_UPGRADE.md](./UI_UPGRADE.md) | 详细的 UI 优化说明 |
| [DESIGN_COMPARISON.md](./DESIGN_COMPARISON.md) | 新旧设计对比 |
| [VISUAL_PREVIEW.md](./VISUAL_PREVIEW.md) | 视觉效果预览 |
| [CHANGELOG.md](./CHANGELOG.md) | 完整变更日志 |

## 🎨 核心组件

### 导航栏
- Sticky 定位 + 玻璃态效果
- 响应式 Tab 切换
- 品牌标识 + 副标题

### 表单系统
- 响应式网格布局 (1-3 列)
- 深色输入框 + Focus 发光环
- 渐变提交按钮

### 数据展示
- Agent 卡片网格 (1-4 列自适应)
- 深色主题表格
- 彩色状态徽章

### 火焰图
- 响应式 SVG 容器
- 渐变背景 + 内阴影
- Hover 效果优化

## 🛠️ 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.0.0 | UI 框架 |
| Vite | 7.0.0 | 构建工具 |
| Tailwind CSS | 4.3.1 | 样式框架 |
| Heroicons | - | 图标系统 |
| Google Fonts | - | 字体服务 |

## 📊 性能指标

- **CSS 体积**: 25.88 KB (gzip: 5.09 KB)
- **JS 体积**: 224.84 KB (gzip: 66.97 KB)
- **构建时间**: ~1.15s
- **首屏渲染**: < 1s

## ♿ 可访问性

- ✅ **对比度**: 7:1 (WCAG AAA)
- ✅ **Keyboard 导航**: 完全支持
- ✅ **Screen Reader**: 语义化 HTML
- ✅ **动画选项**: prefers-reduced-motion

## 📱 浏览器支持

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🎯 Pre-Delivery Checklist

- [x] 无 emoji 作为图标 (使用 SVG)
- [x] cursor-pointer 在所有可点击元素
- [x] Hover 状态 + 平滑过渡 (150-300ms)
- [x] 文本对比度 4.5:1+ (实际 7:1)
- [x] Focus 状态可见
- [x] prefers-reduced-motion 支持
- [x] 响应式: 375px, 768px, 1024px, 1440px

## 🐛 故障排查

### 端口被占用
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### 依赖问题
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 构建失败
确保 Node.js >= 18:
```bash
node --version
```

## 🔄 后续计划

- [ ] 主题切换器 (浅色/深色)
- [ ] 国际化 (i18n)
- [ ] 自定义主题
- [ ] 高级图表 (ECharts)
- [ ] WebSocket 实时更新
- [ ] 数据导出功能

## 📄 License

与主项目保持一致

## 🙏 致谢

- [UI/UX Pro Max Skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) - 设计系统
- [Heroicons](https://heroicons.com/) - SVG 图标
- [Tailwind CSS](https://tailwindcss.com/) - CSS 框架
- [Google Fonts](https://fonts.google.com/) - Fira 字体系列

---

**当前版本**: 2.0.0  
**最后更新**: 2026-06-19  
**设计系统**: UI/UX Pro Max v2.0
