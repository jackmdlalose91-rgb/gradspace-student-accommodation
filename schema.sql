-- Gradspace Supabase schema (with settings for notifications)
create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  role text not null check (role in ('admin','manager','student')),
  full_name text,
  profile_photo text,
  must_change_password boolean default true,
  active boolean default true,
  created_at timestamp default now()
);

create table if not exists students (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  suite text, room text,
  next_of_kin text, kin_phone text, address text,
  rent numeric, utilities numeric,
  created_at timestamp default now()
);

create table if not exists invoices (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  amount numeric not null default 0,
  note text,
  due_date date,
  status text check (status in ('unpaid','paid','overdue')) default 'unpaid',
  created_at timestamp default now()
);

create table if not exists bills (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  amount numeric not null default 0,
  note text,
  created_at timestamp default now()
);

create table if not exists payments (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  amount numeric not null default 0,
  method text, note text,
  paid_at timestamp default now()
);

create table if not exists maintenance (
  id uuid primary key default gen_random_uuid(),
  title text, description text, assignee text,
  cost numeric, status text check (status in ('pending','in_progress','done')) default 'pending',
  photo text, created_at timestamp default now()
);

create table if not exists comments (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  sender text check (sender in ('student','management')),
  message text,
  status text check (status in ('open','closed')) default 'open',
  reply text,
  created_at timestamp default now()
);

create table if not exists settings (
  id uuid primary key default gen_random_uuid(),
  key text unique,
  value jsonb
);
