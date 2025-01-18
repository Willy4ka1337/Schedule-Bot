const express = require('express')
const app = express()
const port = process.env.PORT || 4000;
const { PythonShell } = require('python-shell');

app.get('/', (req, res) => {
    res.send('Hello World!')
})
  
app.listen(port, () => {
    console.log(`Example app listening on port ${port}`)
})


PythonShell.run('main.py', null, (err, results) => {
    if (err) throw err;
    console.log(results);
});