"use client"

import { useState, FormEvent } from "react"
import { signIn } from "next-auth/react"

export default function SignInPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const result = await signIn("credentials", {
      redirect: false,
      username,
      password
    })
    if (!result?.error) {
      window.location.href = '/'
    } else {
      alert("Invalid credentials")
    }
  }

  return (
    <main className="max-w-sm mx-auto mt-10">
      <h1 className="text-2xl mb-4">Sign In</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input 
          placeholder="Username" 
          value={username} 
          onChange={e => setUsername(e.target.value)} 
          className="border p-2 w-full"
        />
        <input 
          type="password" 
          placeholder="Password" 
          value={password} 
          onChange={e => setPassword(e.target.value)} 
          className="border p-2 w-full"
        />
        <button 
          type="submit"
          className="bg-blue-500 text-white px-4 py-2"
        >
          Sign In
        </button>
      </form>
    </main>
  )
}
