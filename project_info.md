# Project Info: AI Productivity Assistant

## What is this project?
This project is an **AI Productivity Assistant**, a smart digital tool designed to help users manage their goals, tasks, and time more effectively. Think of it as a highly intelligent to-do list combined with a personal coach. It not only keeps track of what you need to do but also helps you plan, focus, and analyze your productivity using Artificial Intelligence.

## How does it work? (The Flow)

Imagine you are a user interacting with the app. Here is the step-by-step journey of what happens behind the scenes:

1. **Getting Started (Authentication)**: You log into the application. If you are a new user, you create an account. The system securely remembers who you are.
2. **Setting Big Goals (Commitments)**: You start by defining your main objectives or "Commitments" (e.g., "Write a book", "Learn a new language").
3. **Breaking it Down (AI Planning)**: This is where the magic happens! Instead of manually figuring out every single step, you can ask the AI to help. The AI takes your big goal and automatically breaks it down into smaller, manageable, daily tasks.
4. **Getting to Work (Focus Sessions)**: When you are ready to work, you can start a "Focus Session." This acts like a timer (similar to the Pomodoro technique) to help you do deep work without distractions.
5. **Tracking Progress (Dashboard & Analytics)**: As you complete tasks, you simply click "done." The system updates your progress in real-time. You can then view beautiful charts and graphs to see how productive you have been over time.
6. **Smart Reminders**: The system can also send you reminders so you never miss an important task.

## The Tech Stack (What it's built with)

We use modern, reliable technologies to make sure the app is fast, secure, and smart. Here is a simple breakdown of the ingredients used to build this project:

### The "Frontend" (What the user sees and interacts with)
*   **React (Vite)**: This is the tool we use to build the user interface (buttons, menus, screens). It makes the app feel smooth and responsive, like a native app.
*   **Chart.js**: We use this to draw the beautiful graphs and charts that show your productivity analytics.
*   **CSS & Lucide Icons**: These give the app its sleek design, colors, and recognizable icons.

### The "Backend" (The engine and brain behind the scenes)
*   **FastAPI (Python)**: This is the powerful engine that processes all your requests (like saving a task or starting a timer). It's known for being incredibly fast.
*   **Database (SQLite/Supabase)**: This is the digital filing cabinet where all your data (users, goals, tasks) is safely stored.
*   **Celery & Redis**: These handle background jobs. For example, if the app needs to process something heavy or send you a reminder in the future, it hands that job to these tools so the main app doesn't slow down.

### The "AI Brain" (The smart features)
*   **Google GenAI (Gemini) & LangGraph**: This is the artificial intelligence part. When you ask the app to break down a big goal, it sends that request to these AI tools. They act like a team of virtual assistants, thinking through the problem and returning a structured plan for you to follow.

## Summary for Everyone
In simple terms, this project combines a beautiful, easy-to-use screen (Frontend) with a strong, fast engine (Backend) and a smart, thinking brain (AI) to create the ultimate personal productivity coach. When you click a button, the front tells the back what to do, the back asks the AI for help if needed, saves the result in its filing cabinet (Database), and then tells the front to show you the updated information.
