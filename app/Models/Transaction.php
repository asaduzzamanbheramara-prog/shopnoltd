<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Transaction extends Model
{
    protected $fillable = ['wallet_id','type','amount','status','meta'];
    protected $casts = ['meta'=>'array'];
}
