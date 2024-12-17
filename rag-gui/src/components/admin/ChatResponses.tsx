'use client'

import { useEffect, useState } from "react"

interface ChatResponse {
  id: string
  question: string
  response: string
  user: {
    id: string
    name: string | null
    email: string
  }
  createdAt: string
}

export default function ChatResponses() {
  const [responses, setResponses] = useState<ChatResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchResponses() {
      try {
        const res = await fetch("/api/admin/chat-responses")
        const data = await res.json()
        if (res.ok) {
          setResponses(data)
        }
      } catch (error) {
        console.error("Failed to fetch chat responses:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchResponses()
  }, [])

  if (loading) return <p>Loading chat responses...</p>

  return (
    <div className="overflow-auto max-h-96 border rounded p-4">
      {responses.length === 0 ? (
        <p>No chat responses found.</p>
      ) : (
        <table className="min-w-full table-auto">
          <thead>
            <tr>
              <th className="px-4 py-2">User</th>
              <th className="px-4 py-2">Question</th>
              <th className="px-4 py-2">Response</th>
              <th className="px-4 py-2">Date</th>
            </tr>
          </thead>
          <tbody>
            {responses.map((res) => (
              <tr key={res.id} className="border-t">
                <td className="px-4 py-2">{res.user.name || res.user.email}</td>
                <td className="px-4 py-2">{res.question}</td>
                <td className="px-4 py-2">{res.response}</td>
                <td className="px-4 py-2">{new Date(res.createdAt).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
