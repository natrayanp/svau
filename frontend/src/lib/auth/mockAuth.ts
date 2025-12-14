// src/lib/auth/mockAuth.ts

import { writable } from "svelte/store";

export const mockAuthEnabled = writable(false);
export const mockRole = writable<"admin" | "moderator" | "user">("user");
