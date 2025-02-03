// prisma/seed.ts

import { PrismaClient, Role, SubscriptionTier, SubscriptionStatus } from "@prisma/client"
import { hash } from "bcrypt"

const prisma = new PrismaClient()

async function main() {
  // Define admin and moderator users
  const users = [
    {
      name: "Admin User",
      email: "admin@example.com",
      password: await hash("adminpass", 10),
      role: "ADMIN" as Role,
    },
    {
      name: "Moderator User",
      email: "moderator@example.com",
      password: await hash("modpassword", 10),
      role: "MODERATOR" as Role,
    },
  ]

  for (const user of users) {
    const existingUser = await prisma.user.findUnique({ where: { email: user.email } })
    if (!existingUser) {
      await prisma.user.create({
        data: user,
      })
      console.log(`Created user: ${user.email}`)
    } else {
      console.log(`User already exists: ${user.email}`)
    }
  }

  // Optionally, create other initial data like subscriptions or template answers
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
