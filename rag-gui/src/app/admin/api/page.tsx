'use client'

import { useSession } from "next-auth/react"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import ChatResponses from "@/components/admin/ChatResponses"
import TemplateAnswers from "@/components/admin/TemplateAnswers"

export default function AdminPage() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === "loading") return
    if (!session || (session.user.role !== "ADMIN" && session.user.role !== "MODERATOR")) {
      router.push("/signin")
    }
  }, [session, status, router])

  if (status === "loading") return <p className="text-center">Loading...</p>

  return (
    <main className="max-w-4xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Admin Dashboard</h1>
      {session && (session.user.role === "ADMIN" || session.user.role === "MODERATOR") && (
        <>
          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-2">Chatbot Responses</h2>
            <ChatResponses />
          </section>
          {session.user.role === "ADMIN" && (
            <section>
              <h2 className="text-2xl font-semibold mb-2">Template Answers</h2>
              <TemplateAnswers />
            </section>
          )}
        </>
      )}
    </main>
  )
}
