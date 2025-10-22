@extends('layouts.app')
@section('content')
<h2>System Settings</h2>
@if(session('status'))
<div class="alert alert-success">{{ session('status') }}</div>
@endif
<form method="POST" action="{{ url(env('ADMIN_PATH','/admin').'/settings') }}">
  @csrf
  <div class="mb-3"><label>Supported Locales</label><input name="locales" class="form-control" value="{{ env('SUPPORTED_LOCALES') }}"/></div>
  <div class="mb-3"><label>Supported Currencies</label><input name="currencies" class="form-control" value="{{ env('SUPPORTED_CURRENCIES') }}"/></div>
  <button class="btn btn-primary">Save</button>
</form>
@endsection
