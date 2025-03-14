"use client"

import { useSession } from "next-auth/react"
import { useState, FormEvent, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"

export default function ChatPage() {
  const { data: session, status } = useSession()
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (status === "loading") return
    if (!session) {
      router.push('/signin')
    }
  }, [session, status, router])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const userMessage = input.trim()
    if (!userMessage) return

    // Add user message to the chat
    setMessages(prev => [...prev, { role: "user", content: userMessage }])
    setInput("")
    setLoading(true)

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      })

      if (!response.ok || !response.body) {
        throw new Error("Failed to connect to the chat API.")
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let botMessage = ""

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        botMessage += decoder.decode(value)
        setMessages(prev => {
          const lastBot = prev[prev.length - 1]?.role === "assistant"
            ? prev.slice(0, -1)
            : prev
          return [...lastBot, { role: "assistant", content: botMessage }]
        })
      }

    } catch (error) {
      console.error("Error:", error)
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, something went wrong." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Chat with the Bot</h1>
      <div className="border p-4 mb-4 h-80 overflow-auto bg-gray-50 rounded">
        {messages.map((m, i) => (
          <div key={i} className={`mb-2 ${m.role === "assistant" ? "text-blue-600" : "text-gray-800"}`}>
            <strong>{m.role === "assistant" ? "Bot" : "You"}:</strong> {m.content}
          </div>
        ))}
        {loading && <div className="text-gray-500">Bot is typing...</div>}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          className="border p-2 flex-grow rounded"
          placeholder="Ask something..."
        />
        <button 
          type="submit" 
          className="bg-blue-500 text-white px-4 py-2 rounded"
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </form>
    </main>
  )
}
