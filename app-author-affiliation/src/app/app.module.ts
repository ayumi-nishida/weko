import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule }   from '@angular/forms';
import { HttpModule }    from '@angular/http';
import { AppComponent } from './app.component';
import { Route } from '@angular/compiler/src/core';
import { NgSelectModule } from '@ng-select/ng-select';


@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpModule,
    NgSelectModule
  ],
  exports:[],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule { }
