<?php

use Illuminate\Support\Facades\Route;

Route::get('/', fn() => response('Laravel backend working!', 200));

Route::get('/ping', fn() => response('pong', 200));
