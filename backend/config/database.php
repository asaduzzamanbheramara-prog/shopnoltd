<?php
return [
    'default' => 'mysql',
    'connections' => [
        'mysql' => [
            'host' => env('DB_HOST','127.0.0.1'),
            'database' => env('DB_DATABASE','superapp_db'),
            'username' => env('DB_USERNAME','root'),
            'password' => env('DB_PASSWORD',''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
        ],
    ],
];
?>
