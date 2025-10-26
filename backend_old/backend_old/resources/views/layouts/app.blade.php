<!doctype html>
<html lang="{{ app()->getLocale() }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ config('app.name','ShopNoLtd') }}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light">
<div class="container-fluid">
<a class="navbar-brand" href="/">ShopNoLtd</a>
<ul class="navbar-nav ms-auto">
<li class="nav-item"><a class="nav-link" href="/dashboard">Dashboard</a></li>
</ul>
</div>
</nav>
<div class="container mt-4">@yield('content')</div>
</body>
</html>
