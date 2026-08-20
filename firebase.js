import { initializeApp } from "https://www.gstatic.com/firebasejs/12.1.0/firebase-app.js";

import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
  onAuthStateChanged,
  signOut
} from "https://www.gstatic.com/firebasejs/12.1.0/firebase-auth.js";

import {
  getFirestore,
  doc,
  setDoc,
  addDoc,
  getDocs,
  updateDoc,
  deleteDoc,
  collection,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/12.1.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyAk8sw1izMa86vAnCuLJuvuIDnQknYjaWQ",
  authDomain: "mediscan-ai-f84e9.firebaseapp.com",
  projectId: "mediscan-ai-f84e9",
  storageBucket: "mediscan-ai-f84e9.firebasestorage.app",
  messagingSenderId: "860555782619",
  appId: "1:860555782619:web:77527f96cbd2a9bcee9ffe",
  measurementId: "G-MFXKFX824X"
};


const app = initializeApp(firebaseConfig);

const auth = getAuth(app);

const db = getFirestore(app);


export {
  app,
  auth,
  db,

  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
  onAuthStateChanged,
  signOut,

  doc,
  setDoc,
  addDoc,
  getDocs,
  updateDoc,
  deleteDoc,
  collection,
  serverTimestamp
};