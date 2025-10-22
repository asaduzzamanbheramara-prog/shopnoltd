<?php
namespace App\Http\Middleware;

use Closure; use Illuminate\Support\Facades\App;

class DetectLocale
{
    public function handle($request, Closure $next)
    {
        $supported = explode(',', env('SUPPORTED_LOCALES','en'));
        $cookie = $request->cookie('locale');
        $locale = $cookie ?: $request->getPreferredLanguage($supported) ?: 'en';
        if (!in_array($locale, $supported)) $locale = 'en';
        App::setLocale($locale);
        return $next($request);
    }
}
