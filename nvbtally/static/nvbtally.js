(function(){
    app = angular.module("nvbApp", [])

    app.controller('TabController', ['$log', function($log){
        var tab = this;
        tab.tabsLeft = ['info', 'resolutions', 'votes'];
        tab.tabsRight = ['voters', 'about'];

        tab.set = function(t){
            tab.current = t;
            $log.log('Setting tab to: ' + t);
        }
        tab.set('info');

        tab.is = function(t){
            return (t == tab.current);
        }
    }]);

    app.controller('InfoCtrl', ['$log', '$http', function($log, $http){
        var info = this;

        info.content = {};

        $http.get('/info')
            .success(function(data){
                info.content = data;
                $log.log(data);
            }).error(function(error,and,other,things){
                $log.log(error);
            });
    }]);

    app.controller('ResolutionCtrl', ['$log', '$http', function($log, $http){
        var res = this;

        res.unfinalized = [];
        res.finalized = [];

        $http.get('/resolutions')
            .success(function(data){
                res.unfinalized = data.unfinalized;
                res.finalized = data.finalized;
            }).error(function(error,and,other,things){
            });
    }]);

})();