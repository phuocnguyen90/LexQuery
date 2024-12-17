// src/app/api/auth/register/route.ts

import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"
import { hash } from "bcrypt"

interface RegisterRequest {
  name?: string
  email: string
  password: string
}

export async function POST(req: Request) {
  const { name, email, password }: RegisterRequest = await req.json()

  // Validate input
  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required" }, { status: 400 })
  }

  // Check if user already exists
  const existingUser = await prisma.user.findUnique({ where: { email } })
  if (existingUser) {
    return NextResponse.json({ error: "User already exists" }, { status: 400 })
  }

  // Hash the password
  const hashedPassword = await hash(password, 10)

  // Create the user with default role (GUEST)
  const user = await prisma.user.create({
    data: {
      name,
      email,
      password: hashedPassword,
      role: "GUEST",
    },
  })

  return NextResponse.json({ message: "User registered successfully" }, { status: 201 })
}
