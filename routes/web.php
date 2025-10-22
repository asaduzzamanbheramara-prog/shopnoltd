<?php
use Illuminate\Support\Facades\Route;

Route::get('/', function(){ return view('welcome'); });

Route::group(['prefix' => trim(env('ADMIN_PATH','/admin'), '/'), 'middleware' => ['web','auth','is_admin']], function(){
    Route::get('/', [App\Http\Controllers\Admin\DashboardController::class, 'index']);
    Route::get('/settings', [App\Http\Controllers\Admin\SettingsController::class, 'index']);
    Route::post('/settings', [App\Http\Controllers\Admin\SettingsController::class, 'update']);
});

Route::get('/dashboard', [App\Http\Controllers\User\DashboardController::class,'index'])->middleware('auth');

Route::post('/webhook/stripe', [App\Http\Controllers\PaymentController::class, 'stripeWebhook']);
Route::post('/webhook/paypal', [App\Http\Controllers\PaymentController::class, 'paypalWebhook']);
