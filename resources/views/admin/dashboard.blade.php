@extends('layouts.app')
@section('content')
<h2>Admin Dashboard</h2>
<p>Quick links:</p>
<ul>
  <li><a href="{{ url(env('ADMIN_PATH','/admin').'/settings') }}">System Settings</a></li>
  <li><a href="{{ url(env('ADMIN_PATH','/admin').'/payments') }}">Payments</a></li>
</ul>
@endsection
