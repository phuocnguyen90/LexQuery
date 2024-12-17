'use client'

import { useSession, signIn, signOut } from "next-auth/react"
import { useState, useEffect } from "react"
import prisma from "@/lib/prisma"  // Adjust path as necessary

export default function ProfilePage() {
  const { data: session, status } = useSession()
  const [membership, setMembership] = useState("free")
  const [billing, setBilling] = useState("no active subscription")
  const [usage, setUsage] = useState<{ questionsUsed: number; tokensUsed: number }>({ questionsUsed: 0, tokensUsed: 0 })

  useEffect(() => {
    async function fetchUserData() {
      if (session?.user?.id) {
        // Fetch user subscription and usage
        const res = await fetch(`/api/user/${session.user.id}`)
        if (res.ok) {
          const data = await res.json()
          setMembership(data.subscription?.tier || "free")
          setBilling(data.subscription?.status || "no active subscription")
          setUsage(data.usage || { questionsUsed: 0, tokensUsed: 0 })
        }
      }
    }

    fetchUserData()
  }, [session])

  if (status === "loading") return <p className="text-center">Loading...</p>
  if (!session) {
    return (
      <main className="max-w-2xl mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">Please Sign In</h1>
        <button onClick={() => signIn()} className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
          Sign In
        </button>
      </main>
    )
  }

  // Calculate remaining usage
  const usageLimits = getUsageLimits(session.user.role, membership as any)  // Type assertion as per usage.ts
  const remainingQuestions = usageLimits.maxQuestions - usage.questionsUsed
  const remainingTokens = usageLimits.maxTokens - usage.tokensUsed

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Your Profile</h1>
      <p className="mb-2"><strong>Username:</strong> {session.user?.name}</p>
      <p className="mb-2"><strong>Role:</strong> {session.user?.role || "guest"}</p>
      <p className="mb-2"><strong>Membership:</strong> {membership}</p>
      <p className="mb-4"><strong>Billing:</strong> {billing}</p>

      <div className="mb-4">
        <h2 className="text-xl font-semibold mb-2">Usage Today</h2>
        <p><strong>Questions Used:</strong> {usage.questionsUsed} / {usageLimits.maxQuestions === Infinity ? "Unlimited" : usageLimits.maxQuestions}</p>
        <p><strong>Tokens Used:</strong> {usage.tokensUsed} / {usageLimits.maxTokens === Infinity ? "Unlimited" : usageLimits.maxTokens}</p>
      </div>

      <div className="space-x-2">
        {membership === "free" && (
          <button onClick={() => {/* Implement upgrade logic */}} className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
            Upgrade to Paid
          </button>
        )}
        <button onClick={() => signOut()} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
          Sign Out
        </button>
      </div>
    </main>
  )
}
