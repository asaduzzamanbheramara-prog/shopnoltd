import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export default function Dashboard() {
    const [jobs,setJobs]=useState([]);
    const [workers,setWorkers]=useState([]);

    useEffect(()=>{
        fetch('/api/jobs').then(r=>r.json()).then(setJobs);
        fetch('/api/workers').then(r=>r.json()).then(setWorkers);
    },[]);

    return (
    <div className="min-h-screen p-6 bg-gray-100">
      <h1 className="text-3xl font-bold mb-6">SuperApp Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <motion.div className="bg-white p-6 rounded-2xl shadow-lg" whileHover={{scale:1.03}}>
          <h2>Total Jobs</h2>
          <p className="text-2xl">{jobs.length}</p>
        </motion.div>
        <motion.div className="bg-white p-6 rounded-2xl shadow-lg" whileHover={{scale:1.03}}>
          <h2>Total Workers</h2>
          <p className="text-2xl">{workers.length}</p>
        </motion.div>
        <motion.div className="bg-white p-6 rounded-2xl shadow-lg" whileHover={{scale:1.03}}>
          <h2>Platform Balance</h2>
          <p className="text-2xl">Check platform_accounts table</p>
        </motion.div>
      </div>
    </div>
    );
}
