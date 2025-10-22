<?php
namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Setting;

class SettingsController extends Controller
{
    public function index(){ $locales = explode(',', env('SUPPORTED_LOCALES','en')); return view('admin.settings', compact('locales')); }
    public function update(Request $r){ Setting::updateOrCreate(['key'=>'supported_locales'], ['value'=>$r->input('locales')]); Setting::updateOrCreate(['key'=>'supported_currencies'], ['value'=>$r->input('currencies')]); return redirect()->back()->with('status','Settings saved'); }
}
