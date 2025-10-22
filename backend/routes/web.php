<?php
use Illuminate\Support\Facades\Route;

Route::get('/', function() {
    return response()->json(['message'=>'SuperApp Backend is running']);
});

Route::get('/api/jobs', 'App\Http\Controllers\JobController@index');
Route::get('/api/workers', 'App\Http\Controllers\WorkerController@index');
Route::post('/api/submit-action', 'App\Http\Controllers\ActionController@store');
Route::get('/api/download-db', 'App\Http\Controllers\DatabaseController@download');
?>
