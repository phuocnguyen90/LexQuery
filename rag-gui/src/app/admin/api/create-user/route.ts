// src/app/api/admin/create-user/route.ts

import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"
import { hash } from "bcrypt"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth/auth-options"

interface CreateUserRequest {
  name?: string
  email: string
  password: string
  role: "ADMIN" | "MODERATOR"
}

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)

  // Ensure only admins can create new admin/moderator accounts
  if (!session || session.user.role !== "ADMIN") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { name, email, password, role }: CreateUserRequest = await req.json()

  // Validate input
  if (!email || !password || !role) {
    return NextResponse.json({ error: "Email, password, and role are required." }, { status: 400 })
  }

  // Check if user already exists
  const existingUser = await prisma.user.findUnique({ where: { email } })
  if (existingUser) {
    return NextResponse.json({ error: "User already exists." }, { status: 400 })
  }

  // Hash the password
  const hashedPassword = await hash(password, 10)

  // Create the user
  try {
    const user = await prisma.user.create({
      data: {
        name,
        email,
        password: hashedPassword,
        role,
      },
    })

    return NextResponse.json({ message: "User created successfully.", user }, { status: 201 })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: "Failed to create user." }, { status: 500 })
  }
}
