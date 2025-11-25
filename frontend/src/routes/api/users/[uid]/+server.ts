import { json, type RequestHandler } from '@sveltejs/kit';
import fs from 'fs/promises';
import path from 'path';

const DATA_FILE = path.resolve('static', 'data.json');

// User type
interface User {
  id: string;
  uid?: string;
  name: string;
  email: string;
  createdAt: string;
  updatedAt: string;
  [key: string]: any; // allow extra fields for updates
}

// Structure of the JSON file
interface DataFile {
  users: User[];
}

// Read the JSON file
async function readData(): Promise<DataFile> {
  try {
    const data = await fs.readFile(DATA_FILE, 'utf8');
    return JSON.parse(data) as DataFile;
  } catch {
    return { users: [] };
  }
}

// Write to the JSON file
async function writeData(data: DataFile): Promise<void> {
  await fs.writeFile(DATA_FILE, JSON.stringify(data, null, 2));
}

// GET handler
export const GET: RequestHandler = async ({ params }) => {
  const { uid } = params;
  const data = await readData();

  const user = data.users.find(u => u.uid === uid || u.id === uid);

  if (!user) {
    return new Response('User not found', { status: 404 });
  }

  return json(user);
};

// PUT handler
export const PUT: RequestHandler = async ({ params, request }) => {
  const { uid } = params;
  const updates = await request.json() as Partial<User>;

  const data = await readData();

  const userIndex = data.users.findIndex(u => u.uid === uid || u.id === uid);

  if (userIndex === -1) {
    return new Response('User not found', { status: 404 });
  }

  data.users[userIndex] = {
    ...data.users[userIndex],
    ...updates,
    updatedAt: new Date().toISOString()
  };

  await writeData(data);

  return json(data.users[userIndex]);
};
