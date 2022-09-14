const express = require('express')
var bodyParser = require('body-parser')
const {PythonShell} =require('python-shell'); 
const app = express()
app.use(express.json());
app.use(bodyParser.json());


var options = {};
app.post('/first',(req,res)=>{
    var json = req.body;
    options = {
        mode: 'text', 
        // pythonPath: 'C://Users/AppData/Local/Microsoft/WindowsApps/python.exe',
        // pythonOptions: ['-u'], 
        // scriptPath: 'C://Users/91852/Downloads/wordle-solver-main',
        args: json["guess"]
    }
    console.log(json);
    PythonShell.run('wordle_solver.py', options, function (err, result){
        console.log(err) 
        console.log(result)
        res.send({
            "result": result[0]
        })
    });
    // res.send(json);
})



app.get('/', (req, res) => {
    res.send('Hello World')
})

app.listen('3000', function() {
    console.log('Listening on port 3000...') }
    ) 