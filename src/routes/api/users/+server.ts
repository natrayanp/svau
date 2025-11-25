import { json, type RequestHandler } from '@sveltejs/kit';
import fs from 'fs/promises';
import path from 'path';

const DATA_FILE = path.resolve('static', 'data.json');

// Define the allowed input fields for creating a user
interface CreateUserInput {
  name: string;
  email: string;
}

// Define the full User type stored in JSON
interface User extends CreateUserInput {
  id: string;
  createdAt: string;
  updatedAt: string;
}

// Define the JSON file structure
interface DataFile {
  users: User[];
}

// Utility to read the JSON file
async function readData(): Promise<DataFile> {
  try {
    const data = await fs.readFile(DATA_FILE, 'utf8');
    return JSON.parse(data) as DataFile;
  } catch {
    return { users: [] };
  }
}

// Utility to write to the JSON file
async function writeData(data: DataFile): Promise<void> {
  await fs.writeFile(DATA_FILE, JSON.stringify(data, null, 2));
}

// Validate input to ensure only allowed fields exist
function validateCreateUserInput(input: unknown): input is CreateUserInput {
  return (
    typeof input === 'object' &&
    input !== null &&
    'name' in input &&
    typeof (input as any).name === 'string' &&
    'email' in input &&
    typeof (input as any).email === 'string'
  );
}

// POST handler
export const POST: RequestHandler = async ({ request }) => {
  const input = await request.json();

  if (!validateCreateUserInput(input)) {
    return json({ error: 'Invalid input' }, { status: 400 });
  }

  const data = await readData();

  const newUser: User = {
    ...input,
    id: Date.now().toString(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };

  data.users.push(newUser);
  await writeData(data);

  return json(newUser);
};

// GET handler
export const GET: RequestHandler = async () => {
  const data = await readData();
  return json(data.users);
};
