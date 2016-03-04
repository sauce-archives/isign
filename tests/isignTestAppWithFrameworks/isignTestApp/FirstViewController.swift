//
//  FirstViewController.swift
//  isignTestApp
//
//  Copyright © 2015 Sauce Labs.
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//  http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//

import UIKit
import FontAwesome_swift

class FirstViewController: UIViewController {

    @IBOutlet weak var boltLabel: UILabel!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        boltLabel.font = UIFont.fontAwesomeOfSize(100);
        boltLabel.text = String.fontAwesomeIconWithName(FontAwesome.Bolt);
        boltLabel.textAlignment = NSTextAlignment.Center;
    }

    override func didReceiveMemoryWarning() {
        super.didReceiveMemoryWarning()
        // Dispose of any resources that can be recreated.
    }


}

