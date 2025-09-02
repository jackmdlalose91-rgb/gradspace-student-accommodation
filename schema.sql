-- Gradspace Full Schema

-- Users
create table if not exists users (
  id text primary key,
  username text unique not null,
  email text unique not null,
  role text not null check (role in ('admin','student','staff')),
  password_hash text not null,
  first_login boolean default true
);

-- Students
create table if not exists students (
  id text primary key,
  name text not null,
  email text unique,
  phone text,
  room text,
  join_date date default now()
);

-- Rooms
create table if not exists rooms (
  room_no text primary key,
  capacity int not null default 1,
  status text not null default 'available' check (status in ('available','occupied','maintenance'))
);

-- Invoices
create table if not exists invoices (
  id uuid default gen_random_uuid() primary key,
  student_id text references students(id) on delete cascade,
  amount numeric not null,
  due_date date not null,
  status text default 'unpaid' check (status in ('unpaid','paid','overdue'))
);

-- Maintenance
create table if not exists maintenance (
  id uuid default gen_random_uuid() primary key,
  student_id text references students(id) on delete set null,
  issue text not null,
  status text default 'open' check (status in ('open','in_progress','resolved')),
  created_at timestamp default now()
);

-- Reset logs (placeholders for future email reset flow)
create table if not exists reset_logs (
  id uuid default gen_random_uuid() primary key,
  user_id text references users(id) on delete cascade,
  created_at timestamp default now()
);

create table if not exists reset_tokens (
  id uuid default gen_random_uuid() primary key,
  user_id text references users(id) on delete cascade,
  token text not null,
  expires_at timestamp not null
);

-- Disable RLS (public demo)
alter table users disable row level security;
alter table students disable row level security;
alter table rooms disable row level security;
alter table invoices disable row level security;
alter table maintenance disable row level security;
alter table reset_logs disable row level security;
alter table reset_tokens disable row level security;
