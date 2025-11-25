import { initializeApp } from "firebase/app";
import { getAuth, connectAuthEmulator } from "firebase/auth";
import { getFirestore, connectFirestoreEmulator } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

console.log('Using Firebase emulator:', import.meta.env.VITE_USE_FIREBASE_EMULATOR);
console.log('Auth emulator URL:', import.meta.env.VITE_FIREBASE_AUTH_EMULATOR_URL);
console.log(import.meta.env.VITE_USE_FIREBASE_EMULATOR === "true");
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const firestore = getFirestore(app);

// Connect to emulators in development
if (import.meta.env.VITE_USE_FIREBASE_EMULATOR === "true") {

  console.log(auth);
  console.log('Auth emulator URL:', import.meta.env.VITE_FIREBASE_AUTH_EMULATOR_URL);
  connectAuthEmulator(auth, import.meta.env.VITE_FIREBASE_AUTH_EMULATOR_URL);

  connectFirestoreEmulator(
    firestore,
    import.meta.env.VITE_FIREBASE_AUTH_EMULATOR_URL?.replace("9099", "8080") || "http://firebase-emulator:8080"
  );
  console.log("[Firebase] Connected to emulator");
}
