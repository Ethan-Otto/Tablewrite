import './App.css'
import { Header } from './components/Header'
import { ChatWindow } from './components/ChatWindow'
import { ChatMessage, ChatRole } from './lib/types'

// Test messages to visualize the components
const testMessages: ChatMessage[] = [
  {
    role: ChatRole.SYSTEM,
    content: 'Welcome to the D&D Module Assistant',
    timestamp: new Date().toISOString()
  },
  {
    role: ChatRole.USER,
    content: 'Hello! Can you help me generate a scene for my campaign?',
    timestamp: new Date().toISOString()
  },
  {
    role: ChatRole.ASSISTANT,
    content: 'Of course! I can help you generate atmospheric scenes for your D&D campaign. You can use the /generate-scene command followed by a description, or simply describe what you need in natural language.',
    timestamp: new Date().toISOString()
  }
];

function App() {
  return (
    <div className="min-h-screen bg-[#2d1f15] flex flex-col">
      <Header />
      <ChatWindow messages={testMessages} />
    </div>
  )
}

export default App
