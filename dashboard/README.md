# CapableBench Performance Dashboard

A modern Next.js dashboard for visualizing and analyzing CapableBench performance data.

## Features

- **Real-time performance metrics** - Live updating KPIs and charts
- **Interactive visualizations** - Model leaderboards, score distributions, and task breakdowns  
- **Tagging system** - Automatically tags runs (saturation, format errors, etc.)
- **Advanced filtering** - Search, filter by task type, difficulty, and model
- **Detailed task views** - Full traces, answers, and metadata
- **Professional UX** - Modern design with responsive layout

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Open dashboard**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## How it works

The dashboard automatically reads from your existing CapableBench data structure:
- `data/tasks/` - Task definitions
- `data/answers/` - Gold answers  
- `runs/` - Execution results

It uses your existing `capablebench.viewer` module to generate the data, then enhances it with:
- Automatic tagging of interesting runs
- Real-time updates every 30 seconds
- Interactive filtering and search

## API Endpoints

- `GET /api/dashboard` - Returns all performance data with tags

## Tagging System

Runs are automatically tagged based on:
- **saturation** - Score ≥90% on hard tasks
- **format_error** - Failed to parse answer
- **execution_error** - Non-zero return code  
- **low_score** - Score <30%
- **high_score** - Score >90%

You can extend this by adding manual tags or custom logic in `/api/dashboard/route.ts`.

## Deployment

For production deployment:

```bash
npm run build
npm start
```

Or deploy to Vercel/Netlify for automatic hosting.

## Development

The dashboard is built with:
- **Next.js 15** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **TanStack Query** - Data fetching & caching

Key files:
- `src/app/api/dashboard/route.ts` - Data API
- `src/components/` - Dashboard components
- `src/types/performance.ts` - Type definitions
