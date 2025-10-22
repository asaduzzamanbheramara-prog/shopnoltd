<?php
use Illuminate\Database\Schema\Blueprint; use Illuminate\Support\Facades\Schema;

return new class {
    public function up(){
        Schema::create('settings', function(Blueprint $table){
            $table->id();
            $table->string('key')->unique();
            $table->text('value')->nullable();
            $table->string('type')->default('string');
            $table->foreignId('updated_by')->nullable()->constrained('users');
            $table->timestamps();
        });
    }
    public function down(){ Schema::dropIfExists('settings'); }
};
