// src/types/user.ts

export interface IUser {
    id: string
    name?: string | null
    email: string
    role: Role
    subscription?: ISubscription | null
  }
  
  export interface ISubscription {
    id: string
    tier: SubscriptionTier
    status: SubscriptionStatus
    userId: string
  }
  
  export type Role = "GUEST" | "FREE" | "PAID" | "ADMIN" | "MODERATOR"
  export type SubscriptionTier = "UNLIMITED" | "PAY_AS_YOU_GO" | "PREPAID_BASIC" | "PREPAID_PRO" | "PREPAID_ENTERPRISE"
  export type SubscriptionStatus = "ACTIVE" | "INACTIVE"
  