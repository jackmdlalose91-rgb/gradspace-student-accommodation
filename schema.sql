create extension if not exists "uuid-ossp";

create table if not exists users (
  id text primary key,
  username text unique,
  email text unique,
  role text default 'student',
  password_hash text,
  first_login boolean default true
);

create table if not exists students (
  id text primary key,
  name text not null,
  email text
);

create table if not exists reset_logs (
  id uuid primary key default uuid_generate_v4(),
  student_id text not null,
  student_name text,
  admin_id text not null,
  reset_method text not null,
  timestamp timestamptz default now()
);

create table if not exists reset_tokens (
  id uuid primary key default uuid_generate_v4(),
  email text,
  student_id text,
  token text,
  valid_until timestamptz
);
