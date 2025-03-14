'use client'

import { useSession } from "next-auth/react"
import { useState } from "react"
import { useRouter } from "next/navigation"

export default function SubscriptionPage() {
  const { data: session } = useSession()
  const [selectedTier, setSelectedTier] = useState<string>("")
  const [message, setMessage] = useState<string | null>(null)
  const router = useRouter()

  if (!session) {
    return (
      <main className="max-w-sm mx-auto mt-10 p-4">
        <h1 className="text-2xl mb-4">Please Sign In</h1>
      </main>
    )
  }

  async function handleUpgrade() {
    if (!selectedTier) {
      setMessage("Please select a subscription tier.")
      return
    }

    try {
      const res = await fetch("/api/subscription/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier: selectedTier }),
      })

      const data = await res.json()

      if (!res.ok) {
        setMessage(data.error || "Failed to upgrade subscription.")
      } else {
        setMessage("Subscription upgraded successfully!")
        setTimeout(() => {
          router.refresh()
        }, 2000)
      }
    } catch (error) {
      setMessage("An unexpected error occurred.")
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Manage Subscription</h1>
      {message && <p className="mb-4 text-green-500">{message}</p>}
      <div className="space-y-4">
        <div className="border rounded p-4">
          <h2 className="text-2xl font-semibold mb-2">Select a Subscription Tier</h2>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                name="tier"
                value="PAY_AS_YOU_GO"
                onChange={(e) => setSelectedTier(e.target.value)}
                className="mr-2"
              />
              Pay-as-You-Go
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="tier"
                value="PREPAID_BASIC"
                onChange={(e) => setSelectedTier(e.target.value)}
                className="mr-2"
              />
              Prepaid Basic
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="tier"
                value="PREPAID_PRO"
                onChange={(e) => setSelectedTier(e.target.value)}
                className="mr-2"
              />
              Prepaid Pro
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="tier"
                value="PREPAID_ENTERPRISE"
                onChange={(e) => setSelectedTier(e.target.value)}
                className="mr-2"
              />
              Prepaid Enterprise
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="tier"
                value="UNLIMITED"
                onChange={(e) => setSelectedTier(e.target.value)}
                className="mr-2"
              />
              Unlimited
            </label>
          </div>
        </div>
        <button
          onClick={handleUpgrade}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Upgrade Subscription
        </button>
      </div>
    </main>
  )
}
