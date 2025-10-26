<?php
namespace App\Services\Payment;

use App\Models\Wallet; use App\Models\Transaction; use DB;

class PaymentService
{
    protected $stripe; protected $paypal; protected $manual;
    public function __construct(StripeGateway $stripe, PaypalGateway $paypal, ManualGateway $manual){ $this->stripe = $stripe; $this->paypal = $paypal; $this->manual = $manual; }

    public function createPaymentIntent($user,$amount,$currency,$provider='stripe'){
        if($provider==='paypal') return $this->paypal->createPaymentIntent($user,$amount,$currency);
        if($provider==='manual') return $this->manual->createPaymentIntent($user,$amount,$currency);
        return $this->stripe->createPaymentIntent($user,$amount,$currency);
    }

    public function handleStripeWebhook($payload){ return $this->stripe->handleWebhook($payload); }
    public function handlePaypalWebhook($payload){ return $this->paypal->handleWebhook($payload); }
}
