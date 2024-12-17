'use client'

import { useState, FormEvent, useEffect } from "react"

interface TemplateAnswer {
  id: string
  question: string
  answer: string
  createdAt: string
}

export default function TemplateAnswers() {
  const [templates, setTemplates] = useState<TemplateAnswer[]>([])
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    async function fetchTemplates() {
      try {
        const res = await fetch("/api/admin/chat-responses")
        const data = await res.json()
        if (res.ok) {
          setTemplates(data.templateAnswers || [])
        }
      } catch (error) {
        console.error("Failed to fetch template answers:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchTemplates()
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!question || !answer) {
      setError("Both question and answer are required.")
      return
    }

    try {
      const res = await fetch("/api/admin/chat-responses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, answer }),
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.error || "Failed to create template answer.")
      } else {
        setSuccess("Template answer created successfully!")
        setQuestion("")
        setAnswer("")
        setTemplates((prev) => [...prev, data])
      }
    } catch (error) {
      setError("An unexpected error occurred.")
    }
  }

  if (loading) return <p>Loading template answers...</p>

  return (
    <div>
      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        {error && <p className="text-red-500">{error}</p>}
        {success && <p className="text-green-500">{success}</p>}
        <input
          type="text"
          placeholder="Question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="border p-2 w-full rounded"
          required
        />
        <textarea
          placeholder="Answer"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          className="border p-2 w-full rounded"
          required
        />
        <button
          type="submit"
          className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Add Template Answer
        </button>
      </form>

      <div className="overflow-auto max-h-96 border rounded p-4">
        {templates.length === 0 ? (
          <p>No template answers found.</p>
        ) : (
          <table className="min-w-full table-auto">
            <thead>
              <tr>
                <th className="px-4 py-2">Question</th>
                <th className="px-4 py-2">Answer</th>
                <th className="px-4 py-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((template) => (
                <tr key={template.id} className="border-t">
                  <td className="px-4 py-2">{template.question}</td>
                  <td className="px-4 py-2">{template.answer}</td>
                  <td className="px-4 py-2">{new Date(template.createdAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
