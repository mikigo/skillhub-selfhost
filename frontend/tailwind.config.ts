import type { Config } from 'tailwindcss'

// 颜色变量在 index.css 里存的是 oklch 通道值（`0.21 0.006 285.885`），这里拼回完整颜色。
// 必须用 oklch() 而不是 hsl()：变量是 oklch 的，包错函数名会让声明整条非法被丢弃。
// `/ <alpha-value>` 是 Tailwind 的占位符，bg-primary/20 这类透明度修饰符靠它生效。
const token = (name: string) => `oklch(var(--${name}) / <alpha-value>)`

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      colors: {
        background: token('background'),
        foreground: token('foreground'),
        card: {
          DEFAULT: token('card'),
          foreground: token('card-foreground')
        },
        popover: {
          DEFAULT: token('popover'),
          foreground: token('popover-foreground')
        },
        primary: {
          DEFAULT: token('primary'),
          foreground: token('primary-foreground')
        },
        secondary: {
          DEFAULT: token('secondary'),
          foreground: token('secondary-foreground')
        },
        muted: {
          DEFAULT: token('muted'),
          foreground: token('muted-foreground')
        },
        accent: {
          DEFAULT: token('accent'),
          foreground: token('accent-foreground')
        },
        destructive: token('destructive'),
        // border / input 是写死的灰：index.css 的 base 层也用同样的值兜底
        border: '#e5e7eb',
        input: '#d1d5db',
        ring: token('ring'),
        chart: {
          '1': token('chart-1'),
          '2': token('chart-2'),
          '3': token('chart-3'),
          '4': token('chart-4'),
          '5': token('chart-5')
        },
        sidebar: {
          DEFAULT: token('sidebar'),
          foreground: token('sidebar-foreground'),
          primary: token('sidebar-primary'),
          'primary-foreground': token('sidebar-primary-foreground'),
          accent: token('sidebar-accent'),
          'accent-foreground': token('sidebar-accent-foreground'),
          border: token('sidebar-border'),
          ring: token('sidebar-ring')
        }
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config
