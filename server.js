const express = require('express')
const app = express()
const port = 4000 //process.env.PORT || 4000;

const { PythonShell } = require('python-shell');

app.get('/', (req, res) => {
    res.send('<h1>This is a web service for a Schedule bot</h1><br>Developer: <a href="https://t.me/SchizophreniaCP1251">Willy4ka</a>')
})

app.listen(port, () => {
    console.log(`Example app listening on port ${port}`)
})

PythonShell.run('botstarter.py', null, (err, results) => {
    if (err) throw err;
    console.log(results);
});