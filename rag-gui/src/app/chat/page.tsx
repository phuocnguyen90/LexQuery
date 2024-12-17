"use client"

import { useState, FormEvent, useEffect } from "react"

export default function ChatPage() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const userMessage = input.trim()
    if (!userMessage) return

    // Add user message to the chat
    setMessages(prev => [...prev, { role: "user", content: userMessage }])
    setInput("")
    setLoading(true)

    // Call the chat endpoint
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    })

    const reader = response.body?.getReader()
    if (!reader) {
      setLoading(false)
      return
    }

    let botMessage = ""
    const decoder = new TextDecoder()

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      botMessage += decoder.decode(value)
      // Update message incrementally
      setMessages(prev => {
        const lastBot = prev[prev.length - 1]?.role === "assistant"
          ? prev.slice(0, -1)
          : prev
        return [...lastBot, { role: "assistant", content: botMessage }]
      })
    }

    setLoading(false)
  }

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Chat with the Bot</h1>
      <div className="border p-4 mb-4 h-80 overflow-auto">
        {messages.map((m, i) => (
          <div key={i} className={`mb-2 ${m.role === "assistant" ? "text-blue-600" : "text-gray-800"}`}>
            <strong>{m.role === "assistant" ? "Bot" : "You"}:</strong> {m.content}
          </div>
        ))}
        {loading && <div className="text-gray-500">Bot is typing...</div>}
      </div>
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          className="border flex-grow p-2"
          placeholder="Ask something..."
        />
        <button type="submit" className="bg-blue-500 text-white px-4 py-2" disabled={!input.trim()}>
          Send
        </button>
      </form>
    </main>
  )
}
