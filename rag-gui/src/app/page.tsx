"use client"

import { useSession, signOut } from "next-auth/react"
import Link from "next/link"

export default function HomePage() {
  const { data: session, status } = useSession()

  if (status === 'loading') return <p>Loading...</p>

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Welcome to My RAG App</h1>
      {session ? (
        <div>
          <p>Hello, {session.user?.name}!</p>
          <p>Your role: {session.user.role}</p>
          <div className="space-x-2 mt-4">
            <Link href="/chat" className="bg-green-500 text-white px-4 py-2 rounded">
              Go to Chat
            </Link>
            <Link href="/profile" className="bg-yellow-500 text-white px-4 py-2 rounded">
              Profile
            </Link>
            <button 
              onClick={() => signOut()} 
              className="bg-red-500 text-white px-4 py-2 rounded"
            >
              Sign Out
            </button>
          </div>
        </div>
      ) : (
        <div>
          <p>You are not signed in.</p>
          <Link href="/signin" className="bg-blue-500 text-white px-4 py-2 rounded">
            Sign In
          </Link>
        </div>
      )}
    </main>
  )
}
