<?php

use Illuminate\Support\Facades\Route;

Route::get('/', fn() => 'Minimal Laravel backend ready');

Route::get('/ping', fn() => response('pong', 200));
