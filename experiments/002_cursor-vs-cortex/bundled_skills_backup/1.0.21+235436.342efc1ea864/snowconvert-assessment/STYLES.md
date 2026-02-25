# Styling Guide for SnowConvert Assessment Reports

## Color Palette (Snowflake Official)

### Primary
- `#29B5E8` - Snowflake Blue (headers, primary buttons, navigation)
- `#FFFFFF` - White (backgrounds, text on dark)
- `#000000` - Black (primary text, borders)

### Secondary Blues
- `#11567F` - Dark Blue (hover states, secondary elements)
- `#003545` - Deep Blue (accents)
- `#102E46` - Navy (dark backgrounds, footer)

### Accent Colors
- `#FF9F36` - Orange (warnings, CTAs, highlights)
- `#71D3DC` - Light Cyan (charts, data viz)
- `#7D44CF` - Purple (metrics, data viz)
- `#D45B90` - Pink (emphasis, data viz)

### Neutral
- `#8A999E` - Gray (secondary text, borders, disabled)
- `#24323D` - Dark Gray (secondary backgrounds)

## Layout Standards

### Sidebar Navigation
- Width: `280px` or `w-70` in Tailwind
- Background: `#102E46`
- Fixed position
- Text: White `#FFFFFF`
- Active link: `#29B5E8` background

### Content Area
- Left margin: `280px` to accommodate sidebar
- Padding: `2rem` or `p-8`
- Background: `#FFFFFF`
- Max width: `1400px`

### Typography
- Headings: `font-bold`, color `#000000` or `#11567F`
- Body: `font-normal`, color `#000000`, line-height `1.6`
- Code/Monospace: Use `font-mono`, background `#F5F5F5`

### Cards & Containers
- Border: `1px solid #8A999E`
- Border radius: `8px` or `rounded-lg`
- Shadow: `0 2px 4px rgba(0,0,0,0.1)`
- Padding: `1.5rem` or `p-6`

### Tables
- Header background: `#29B5E8`
- Header text: `#FFFFFF`
- Row borders: `#8A999E`
- Striped rows: alternating `#FFFFFF` and `#F9FAFB`
- Hover: `#E5F6FD` (light blue tint)

### Charts & Data Visualization
Use accent colors in sequence:
1. `#29B5E8` (Primary Blue)
2. `#71D3DC` (Light Cyan)
3. `#7D44CF` (Purple)
4. `#D45B90` (Pink)
5. `#FF9F36` (Orange)

### Buttons
- Primary: Background `#29B5E8`, text `#FFFFFF`, hover `#11567F`
- Secondary: Background `#8A999E`, text `#FFFFFF`, hover `#24323D`
- Danger: Background `#FF9F36`, text `#FFFFFF`

## Accessibility

- Maintain WCAG AA contrast ratios (4.5:1 for text)
- All interactive elements must have focus states
- Use semantic HTML (`<nav>`, `<main>`, `<article>`)

## Tailwind CSS Classes Reference

If using Tailwind via CDN:

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          'sf-blue': '#29B5E8',
          'sf-dark-blue': '#11567F',
          'sf-deep-blue': '#003545',
          'sf-navy': '#102E46',
          'sf-orange': '#FF9F36',
          'sf-cyan': '#71D3DC',
          'sf-purple': '#7D44CF',
          'sf-pink': '#D45B90',
          'sf-gray': '#8A999E',
          'sf-dark-gray': '#24323D'
        }
      }
    }
  }
</script>
```

## Example Component Templates

### Section Header
```html
<h2 class="text-3xl font-bold text-sf-dark-blue mb-6 border-b-2 border-sf-blue pb-2">
  Section Title
</h2>
```

### Metric Card
```html
<div class="bg-white border border-sf-gray rounded-lg p-6 shadow-sm">
  <h3 class="text-lg font-semibold text-sf-dark-blue mb-2">Metric Name</h3>
  <p class="text-4xl font-bold text-sf-blue">1,234</p>
  <p class="text-sm text-sf-gray mt-2">Description</p>
</div>
```

### Data Table
```html
<table class="w-full border-collapse">
  <thead class="bg-sf-blue text-white">
    <tr>
      <th class="p-3 text-left">Column</th>
    </tr>
  </thead>
  <tbody class="text-sm">
    <tr class="border-b border-sf-gray hover:bg-blue-50">
      <td class="p-3">Data</td>
    </tr>
  </tbody>
</table>
```

