<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Services\Payment\PaymentService;

class PaymentController extends Controller
{
    protected $service;
    public function __construct(PaymentService $service){ $this->service = $service; }

    public function createIntent(Request $r){
        $user = auth()->user();
        $amount = (float)$r->input('amount', 0);
        $currency = $r->input('currency','USD');
        return response()->json($this->service->createPaymentIntent($user,$amount,$currency));
    }

    public function stripeWebhook(Request $r){ return $this->service->handleStripeWebhook($r->all()); }
    public function paypalWebhook(Request $r){ return $this->service->handlePaypalWebhook($r->all()); }
}
